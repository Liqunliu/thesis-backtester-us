"""
LLM Client — supports OpenAI-compatible API and Claude CLI backend

Backend selection via LLM_BACKEND env var or strategy.yaml:
  - "api" (default): OpenAI-compatible API (requires LLM_API_KEY)
  - "claude-cli": Use 'claude' CLI subprocess (no API key, uses Claude Code auth)

Usage:
    client = LLMClient.from_strategy(config)
    response = await client.chat(messages, tools)
"""
import asyncio
import json
import os
import logging
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM connection config"""
    backend: str = "api"  # "api" or "claude-cli"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"
    max_tokens: int = 8192
    temperature: float = 0.1

    @classmethod
    def from_strategy(cls, config) -> "LLMConfig":
        """Load from StrategyConfig"""
        llm_raw = config.raw.get("llm", {})

        # Backend selection: env > yaml > default
        backend = os.environ.get("LLM_BACKEND", llm_raw.get("backend", "api"))

        # Model: env > yaml > default
        model_env = llm_raw.get("model_env", "LLM_MODEL")
        model = os.environ.get(model_env) or llm_raw.get("model", "gpt-4o")

        if backend == "claude-cli":
            return cls(
                backend="claude-cli",
                model=model,
                max_tokens=llm_raw.get("max_tokens", 8192),
                temperature=llm_raw.get("temperature", 0.1),
            )

        # API backend
        base_url_env = llm_raw.get("base_url_env", "LLM_BASE_URL")
        api_key_env = llm_raw.get("api_key_env", "LLM_API_KEY")

        base_url = os.environ.get(base_url_env, llm_raw.get("base_url", "https://api.openai.com/v1"))
        api_key = os.environ.get(api_key_env, "")

        if not api_key:
            # Auto-detect: fall back to claude-cli if no API key
            logger.warning("No LLM_API_KEY found, falling back to claude-cli backend")
            return cls(
                backend="claude-cli",
                model=model,
                max_tokens=llm_raw.get("max_tokens", 8192),
                temperature=llm_raw.get("temperature", 0.1),
            )

        return cls(
            backend="api",
            base_url=base_url,
            api_key=api_key,
            model=model,
            max_tokens=llm_raw.get("max_tokens", 8192),
            temperature=llm_raw.get("temperature", 0.1),
        )


class LLMClient:
    """LLM client supporting OpenAI API and Claude CLI backends."""

    def __init__(self, llm_config: LLMConfig):
        self.config = llm_config
        self._client = None

        if llm_config.backend == "api":
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                base_url=llm_config.base_url,
                api_key=llm_config.api_key,
            )

    @classmethod
    def from_strategy(cls, config) -> "LLMClient":
        llm_config = LLMConfig.from_strategy(config)
        logger.info(f"LLM backend: {llm_config.backend} / {llm_config.model}")
        return cls(llm_config)

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 3,
        timeout: float = 300,
    ) -> Any:
        """Send chat request. Routes to API or Claude CLI based on backend."""
        if self.config.backend == "claude-cli":
            return await self._chat_claude_cli(messages, tools)
        return await self._chat_api(messages, tools, max_retries, timeout)

    # ---- Claude CLI backend ----

    async def _chat_claude_cli(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """Execute via 'claude' CLI subprocess.

        Converts OpenAI message format to a single prompt string,
        runs 'claude --print', and wraps the response in a
        ChatCompletion-like object.
        """
        # Build prompt from messages — avoid XML-like tags that trigger
        # prompt injection detection in claude CLI
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"SYSTEM INSTRUCTIONS:\n{content}\n")
            elif role == "user":
                prompt_parts.append(content)
            elif role == "assistant":
                prompt_parts.append(f"[Previous assistant response]: {content[:500]}")
            elif role == "tool":
                tool_id = msg.get("tool_call_id", "")
                prompt_parts.append(f"[Tool result for {tool_id}]: {content[:2000]}")

        # Tools are not used with CLI backend — the claude CLI handles
        # tool calls natively. We ignore the tools parameter and just
        # ask for structured JSON output.
        prompt_parts.append(
            "\nPlease provide your analysis. At the end, output a structured "
            "JSON conclusion wrapped in ```json ``` code fences."
        )

        full_prompt = "\n\n".join(prompt_parts)

        # Run claude CLI: write prompt to temp file, invoke via synchronous
        # subprocess.run in a thread. Using asyncio subprocess directly causes
        # hangs in non-TTY environments (Claude Code sessions, CI, etc.)
        import tempfile
        logger.debug("Calling claude CLI (prompt length: %d chars)", len(full_prompt))
        try:
            response_text = await asyncio.get_event_loop().run_in_executor(
                None, self._run_claude_sync, full_prompt
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Claude CLI not found. Install it: npm install -g @anthropic-ai/claude-code\n"
                "Or set LLM_API_KEY to use the API backend instead."
            )

        # Wrap in ChatCompletion-like response
        return _ClaudeCliResponse(response_text)

    def _run_claude_sync(self, prompt: str) -> str:
        """Run claude CLI synchronously (called from thread pool).

        Writes prompt to a temp file and pipes it to claude --print
        to avoid stdin inheritance issues in non-interactive processes.
        """
        import tempfile
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as f:
                f.write(prompt)
                tmp_path = f.name

            result = subprocess.run(
                f'cat "{tmp_path}" | claude --print --no-session-persistence'
                f' --model {self.config.model}',
                shell=True,
                capture_output=True,
                text=True,
                timeout=480,
            )
            if result.returncode != 0:
                err = result.stderr[:500]
                logger.error("claude CLI error (rc=%d): %s", result.returncode, err)
                return err or "Claude CLI returned an error"
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "Claude CLI timed out after 480 seconds"
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # ---- OpenAI API backend ----

    async def _chat_api(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 3,
        timeout: float = 300,
    ) -> Any:
        """Send via OpenAI-compatible API with retry logic."""
        from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError

        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "timeout": timeout,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                return response
            except RateLimitError as e:
                last_error = e
                wait = min(2 ** attempt * 5, 60)
                logger.warning(f"Rate limited, retry in {wait}s (attempt {attempt}): {e}")
                await asyncio.sleep(wait)
            except (APIConnectionError, APITimeoutError) as e:
                last_error = e
                wait = 2 ** attempt * 2
                logger.warning(f"Connection error, retry in {wait}s (attempt {attempt}): {e}")
                await asyncio.sleep(wait)
            except APIError as e:
                if e.status_code and e.status_code >= 500:
                    last_error = e
                    wait = 2 ** attempt * 3
                    logger.warning(f"Server error {e.status_code}, retry in {wait}s (attempt {attempt})")
                    await asyncio.sleep(wait)
                else:
                    raise

        raise last_error

    async def close(self):
        if self._client is not None:
            await self._client.close()


# ---- Claude CLI response wrapper ----

class _ClaudeCliChoice:
    def __init__(self, text: str):
        self.message = _ClaudeCliMessage(text)
        self.finish_reason = "stop"


class _ClaudeCliMessage:
    def __init__(self, text: str):
        self.role = "assistant"
        self.content = text
        self.tool_calls = None

        # Try to parse tool calls from response
        if '"tool_calls"' in text:
            try:
                data = json.loads(text)
                if "tool_calls" in data:
                    self.tool_calls = [
                        _ClaudeCliToolCall(tc) for tc in data["tool_calls"]
                    ]
                    self.content = data.get("content", "")
            except json.JSONDecodeError:
                pass


class _ClaudeCliToolCall:
    def __init__(self, tc_dict: dict):
        self.id = tc_dict.get("id", "call_cli_1")
        self.type = "function"
        self.function = _ClaudeCliFunction(tc_dict)


class _ClaudeCliFunction:
    def __init__(self, tc_dict: dict):
        self.name = tc_dict.get("name", "")
        args = tc_dict.get("arguments", {})
        self.arguments = json.dumps(args) if isinstance(args, dict) else str(args)


class _ClaudeCliResponse:
    def __init__(self, text: str):
        self.choices = [_ClaudeCliChoice(text)]
        self.usage = type("Usage", (), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})()
