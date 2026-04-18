"""EDGAR filing date and footnote integration.

Two capabilities:
  1. Filing date lookup (for backtest time-boundary enforcement)
  2. 10-K/10-Q footnote extraction (for qualitative analysis)

Filing dates: Fetches SEC filing dates (when a 10-K/10-Q was actually filed) so
the backtest engine can filter financial data by announcement date, not just
period end date. This prevents look-ahead bias.

Footnotes: Downloads the latest 10-K/10-Q HTML filing and extracts 7 sections
(restricted cash, AR/credit losses, related party, commitments, non-recurring,
MD&A, subsidiaries) using tiered parsing with multiple fallback strategies.

Requires:
    SEC_EDGAR_USER_AGENT environment variable (e.g., "Name email@example.com")
    beautifulsoup4 + lxml (optional, for footnote parsing only)
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("data") / "bloomberg" / "filing_dates"
_FILING_CACHE_DIR = Path("data") / "cache" / "us"
_SEC_BASE = "https://data.sec.gov"
_SEC_WWW = "https://www.sec.gov"
_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
_RATE_LIMIT_SECS = 0.15  # SEC asks for max 10 requests/sec
_FILING_CACHE_TTL_DAYS = 90  # Cache downloaded filings for 90 days

# CIK lookup cache (populated once)
_cik_cache: Optional[dict] = None

# Acceptable form types for annual / quarterly reports
_ANNUAL_FORM_TYPES = {"10-K", "10-K/A", "20-F", "20-F/A"}
_QUARTERLY_FORM_TYPES = {"10-Q", "10-Q/A", "6-K", "6-K/A"}


def _get_headers() -> dict:
    agent = os.environ.get("SEC_EDGAR_USER_AGENT", "")
    if not agent:
        raise EnvironmentError(
            "SEC_EDGAR_USER_AGENT not set. "
            "Set to 'YourName your@email.com' per SEC guidelines."
        )
    return {"User-Agent": agent, "Accept-Encoding": "gzip, deflate"}


def _rate_limited_get(url: str, timeout: int = 30) -> requests.Response:
    """Make a rate-limited GET request to SEC EDGAR."""
    time.sleep(_RATE_LIMIT_SECS)
    resp = requests.get(url, headers=_get_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp


def _lookup_cik(ticker: str) -> Optional[str]:
    """Look up CIK number for a ticker from SEC's company_tickers.json."""
    global _cik_cache
    if _cik_cache is None:
        resp = requests.get(_CIK_URL, headers=_get_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _cik_cache = {}
        for entry in data.values():
            t = entry.get("ticker", "").upper()
            cik = str(entry.get("cik_str", ""))
            _cik_cache[t] = cik.zfill(10)
        time.sleep(_RATE_LIMIT_SECS)

    return _cik_cache.get(ticker.upper())


# ===================================================================
# Filing date lookup (existing functionality)
# ===================================================================

def fetch_filing_dates(
    ticker: str,
    form_types: tuple = ("10-K", "10-Q", "20-F"),
) -> Optional[pd.DataFrame]:
    """Fetch filing dates from SEC EDGAR for a ticker.

    Returns DataFrame with columns: end_date, filing_date, form_type
    Cached in Parquet after first fetch.
    """
    # Check cache
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _CACHE_DIR / f"{ticker.upper()}.parquet"
    if cache_file.exists():
        cached = pd.read_parquet(cache_file)
        # Use cache if < 30 days old
        mtime = cache_file.stat().st_mtime
        age_days = (time.time() - mtime) / 86400
        if age_days < 30:
            return cached

    cik = _lookup_cik(ticker)
    if not cik:
        logger.warning("CIK not found for %s", ticker)
        return None

    # Fetch submissions
    url = f"{_SEC_BASE}/submissions/CIK{cik}.json"
    try:
        resp = requests.get(url, headers=_get_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        time.sleep(_RATE_LIMIT_SECS)
    except Exception as e:
        logger.warning("EDGAR submissions fetch failed for %s: %s", ticker, e)
        return None

    # Parse recent filings
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    periods = recent.get("reportDate", [])

    rows = []
    for form, filing_date, period in zip(forms, dates, periods):
        if form in form_types and period:
            rows.append({
                "end_date": period,
                "filing_date": filing_date,
                "form_type": form,
            })

    if not rows:
        logger.warning("No %s filings found for %s", form_types, ticker)
        return None

    df = pd.DataFrame(rows)
    df["end_date"] = pd.to_datetime(df["end_date"]).dt.strftime("%Y-%m-%d")
    df["filing_date"] = pd.to_datetime(df["filing_date"]).dt.strftime("%Y-%m-%d")

    # Cache
    df.to_parquet(cache_file, index=False)
    logger.info("Cached %d filing dates for %s", len(df), ticker)

    return df


# ===================================================================
# Filing download
# ===================================================================

def download_filing(ticker: str, form_type: str = "10-K") -> Optional[Path]:
    """Download the latest filing of a given type from SEC EDGAR.

    Finds the latest filing via the SEC submissions API, downloads the
    primary HTML document, and saves it to data/cache/us/{TICKER}/.

    The downloaded file is cached with a 90-day TTL -- if the cached file
    exists and is less than 90 days old, the download is skipped.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL').
        form_type: SEC form type -- '10-K' or '10-Q' (default '10-K').

    Returns:
        Path to the downloaded HTML file, or None if download fails.
    """
    ticker_upper = ticker.upper()

    # Determine acceptable form types
    if form_type in ("10-K", "20-F"):
        acceptable = _ANNUAL_FORM_TYPES
    elif form_type in ("10-Q", "6-K"):
        acceptable = _QUARTERLY_FORM_TYPES
    else:
        acceptable = {form_type, f"{form_type}/A"}

    form_short = form_type.replace("-", "").replace("/", "")

    # Check cache
    cache_dir = _FILING_CACHE_DIR / ticker_upper
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_file = cache_dir / f"{ticker_upper}_{form_short}.html"

    if cached_file.exists():
        age_days = (time.time() - cached_file.stat().st_mtime) / 86400
        if age_days < _FILING_CACHE_TTL_DAYS:
            logger.debug("Using cached filing: %s (%.0f days old)", cached_file, age_days)
            return cached_file

    # CIK lookup
    cik = _lookup_cik(ticker_upper)
    if not cik:
        logger.warning("CIK not found for %s -- cannot download filing", ticker_upper)
        return None

    # Fetch submissions index
    url = f"{_SEC_BASE}/submissions/CIK{cik}.json"
    try:
        resp = _rate_limited_get(url, timeout=15)
        submissions = resp.json()
    except Exception as e:
        logger.warning("EDGAR submissions fetch failed for %s: %s", ticker_upper, e)
        return None

    # Find the latest matching filing
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    filing_url = None
    for i, form in enumerate(forms):
        if form in acceptable:
            if i >= len(primary_docs) or not primary_docs[i]:
                continue
            acc = accessions[i].replace("-", "")
            doc = primary_docs[i]
            filing_url = (
                f"{_SEC_WWW}/Archives/edgar/data/{cik.lstrip('0')}/{acc}/{doc}"
            )
            break

    if filing_url is None:
        logger.warning(
            "No %s filing found for %s (CIK %s)", form_type, ticker_upper, cik
        )
        return None

    # Download the filing
    try:
        resp = _rate_limited_get(filing_url, timeout=60)
    except Exception as e:
        logger.warning("Filing download failed for %s: %s", ticker_upper, e)
        return None

    cached_file.write_bytes(resp.content)
    file_size = cached_file.stat().st_size
    logger.info(
        "Downloaded %s filing for %s (%s bytes): %s",
        form_type, ticker_upper, f"{file_size:,}", cached_file,
    )

    if file_size < 1000:
        logger.warning(
            "Filing for %s is unusually small (%d bytes) -- may be invalid",
            ticker_upper, file_size,
        )

    return cached_file


# ===================================================================
# Filing parser -- 10-K/10-Q footnote extraction
# ===================================================================

# Section definitions: (id, display_name, keyword_patterns, is_note)
_SECTION_DEFS: List[Tuple[str, str, List[str], bool]] = [
    (
        "P2",
        "Restricted Cash",
        [r"restricted\s+cash"],
        True,
    ),
    (
        "P3",
        "Accounts Receivable & Credit Losses",
        [r"accounts?\s+receivable", r"allowance\s+for\s+(?:doubtful|credit)", r"credit\s+loss"],
        True,
    ),
    (
        "P4",
        "Related Party Transactions",
        [r"related\s+part(?:y|ies)"],
        True,
    ),
    (
        "P6",
        "Commitments & Contingencies",
        [r"commitments?\s+and\s+contingenc", r"litigation", r"legal\s+proceedings"],
        True,
    ),
    (
        "P13",
        "Non-Recurring Items",
        [r"restructuring", r"impairment", r"goodwill\s+impairment"],
        True,
    ),
    (
        "MDA",
        "Management's Discussion & Analysis",
        [
            r"management.s\s+discussion",
            r"item\s+7[^a]",
            r"item\s*7\.",
            r"item\s+5[^a]",
            r"operating\s+and\s+financial\s+review",   # 20-F
            r"item\s+2[^0-9a-z].*(?:discussion|analysis)",  # 10-Q
        ],
        False,
    ),
    (
        "SUB",
        "Subsidiaries",
        [r"exhibit\s+21", r"significant\s+subsidiar", r"list\s+of\s+subsidiar"],
        False,
    ),
]

_MAX_SECTION_CHARS = 30_000


def _check_bs4():
    """Check that beautifulsoup4 and lxml are available."""
    try:
        from bs4 import BeautifulSoup  # noqa: F401
        return True
    except ImportError:
        logger.warning(
            "beautifulsoup4 is required for EDGAR footnote parsing. "
            "Install with: pip install beautifulsoup4 lxml"
        )
        return False


def _get_text(el) -> str:
    """Get clean text from a BeautifulSoup element."""
    return el.get_text(separator=" ", strip=True)


def _is_heading(el) -> bool:
    """Check if element is a heading or heading-like styled element."""
    if el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return True
    if el.name == "p":
        bold = el.find(["b", "strong"])
        if bold and len(_get_text(bold)) > 5:
            para_text = _get_text(el)
            bold_text = _get_text(bold)
            if len(bold_text) / max(len(para_text), 1) > 0.7:
                return True
    return False


def _table_to_markdown(table) -> str:
    """Convert an HTML table to markdown format."""
    rows = table.find_all("tr")
    if not rows:
        return ""

    md_rows = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        cell_texts = [_get_text(c).replace("|", "/") for c in cells]
        md_rows.append("| " + " | ".join(cell_texts) + " |")

    if len(md_rows) >= 1:
        n_cols = md_rows[0].count("|") - 1
        sep = "| " + " | ".join(["---"] * max(n_cols, 1)) + " |"
        md_rows.insert(1, sep)

    return "\n".join(md_rows)


def _extract_section_content(start_el, max_chars: int = _MAX_SECTION_CHARS) -> str:
    """Extract text content starting from an element until next heading.

    Converts tables to markdown. Truncates at max_chars.
    """
    from bs4 import NavigableString, Tag

    parts: List[str] = []
    total_chars = 0

    # Determine the heading level to stop at
    stop_levels: set = set()
    if start_el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(start_el.name[1])
        stop_levels = {f"h{i}" for i in range(1, level + 1)}

    current = start_el.next_sibling
    while current and total_chars < max_chars:
        if isinstance(current, NavigableString):
            text = str(current).strip()
            if text:
                parts.append(text)
                total_chars += len(text)
        elif isinstance(current, Tag):
            # Stop at next heading of same or higher level
            if current.name in stop_levels:
                break
            if _is_heading(current) and stop_levels:
                break

            # Handle tables specially
            if current.name == "table":
                md_table = _table_to_markdown(current)
                parts.append(md_table)
                total_chars += len(md_table)
            else:
                text = _get_text(current)
                if text:
                    parts.append(text)
                    total_chars += len(text)

                # Also check for nested tables
                for nested_table in current.find_all("table"):
                    md_table = _table_to_markdown(nested_table)
                    parts.append(md_table)
                    total_chars += len(md_table)

        current = current.next_sibling

    result = "\n\n".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n\n[... truncated at 30,000 chars ...]"
    return result


# --- Section-finding strategies (tiered fallback) ---

def _find_by_toc(soup, patterns: List[str]):
    """Strategy 1: Find section via Table of Contents anchor links."""
    for link in soup.find_all("a", href=True):
        link_text = _get_text(link)
        for pattern in patterns:
            if re.search(pattern, link_text, re.IGNORECASE):
                href = link["href"]
                if href.startswith("#"):
                    target_id = href[1:]
                    target = soup.find(id=target_id)
                    if target is None:
                        target = soup.find("a", {"name": target_id})
                    if target:
                        return target
    return None


def _find_by_headings(soup, patterns: List[str]):
    """Strategy 2: Find section via heading tags matching patterns."""
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = _get_text(heading)
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return heading
    return None


def _find_by_styled_paragraphs(soup, patterns: List[str]):
    """Strategy 3: Find section via bold-styled paragraphs."""
    for p in soup.find_all("p"):
        bold = p.find(["b", "strong"])
        if not bold:
            continue
        text = _get_text(bold)
        if len(text) < 5:
            continue
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return p
    return None


def _find_by_text_search(soup, patterns: List[str]):
    """Strategy 4: Full-text keyword search -- find first significant match."""
    body = soup.find("body") or soup
    for el in body.find_all(["p", "div", "span", "td"], limit=5000):
        text = _get_text(el)
        if len(text) < 20:
            continue
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return el
    return None


def _extract_section(
    soup,
    section_id: str,
    section_name: str,
    patterns: List[str],
    is_note: bool,
) -> Dict[str, Any]:
    """Extract a section using tiered fallback strategies.

    Returns dict with: id, name, found, strategy, content, char_count
    """
    strategies = [
        ("toc_anchor", _find_by_toc),
        ("heading_tag", _find_by_headings),
        ("styled_paragraph", _find_by_styled_paragraphs),
        ("text_search", _find_by_text_search),
    ]

    for strategy_name, strategy_fn in strategies:
        start_el = strategy_fn(soup, patterns)
        if start_el:
            content = _extract_section_content(start_el)
            if content and len(content.strip()) > 50:
                return {
                    "id": section_id,
                    "name": section_name,
                    "found": True,
                    "strategy": strategy_name,
                    "content": content.strip(),
                    "char_count": len(content.strip()),
                }

    return {
        "id": section_id,
        "name": section_name,
        "found": False,
        "strategy": None,
        "content": "",
        "char_count": 0,
    }


def parse_filing_sections(html_path: Path) -> dict:
    """Parse an SEC filing HTML and extract all target footnote sections.

    Uses a tiered parsing strategy with 4 fallback levels:
      1. Table of Contents anchors (section jump)
      2. Heading tags (<h1>-<h6>) matching patterns
      3. Styled <p><b> paragraphs
      4. Full-text keyword search

    Converts HTML tables to markdown. Truncates sections at 30,000 chars.

    Args:
        html_path: Path to the downloaded 10-K/10-Q HTML file.

    Returns:
        Dict with keys: filing_path, parsed_at, sections (list of section dicts),
        summary (found_count, total_count, sections_found, sections_missing).
        Returns empty dict if beautifulsoup4 is not installed.
    """
    if not _check_bs4():
        return {}

    from bs4 import BeautifulSoup

    if not html_path.exists():
        logger.warning("Filing not found: %s", html_path)
        return {}

    logger.info("Parsing filing: %s (%s bytes)", html_path, f"{html_path.stat().st_size:,}")

    html_content = html_path.read_bytes()

    # Try lxml parser first (faster), fall back to html.parser
    try:
        soup = BeautifulSoup(html_content, "lxml")
    except Exception:
        soup = BeautifulSoup(html_content, "html.parser")

    sections = []
    found_ids = []

    for section_id, section_name, patterns, is_note in _SECTION_DEFS:
        result = _extract_section(soup, section_id, section_name, patterns, is_note)
        sections.append(result)
        if result["found"]:
            found_ids.append(section_id)
            logger.debug(
                "[%s] Found: %s (%s, %s chars)",
                section_id, section_name, result["strategy"], f"{result['char_count']:,}",
            )
        else:
            logger.debug("[%s] Not found: %s", section_id, section_name)

    logger.info(
        "Parsed %d/%d sections from %s",
        len(found_ids), len(_SECTION_DEFS), html_path.name,
    )

    return {
        "filing_path": str(html_path),
        "parsed_at": datetime.now().isoformat(),
        "sections": sections,
        "summary": {
            "found_count": len(found_ids),
            "total_count": len(_SECTION_DEFS),
            "sections_found": found_ids,
            "sections_missing": [s[0] for s in _SECTION_DEFS if s[0] not in found_ids],
        },
    }


# ===================================================================
# Formatting and high-level API
# ===================================================================

def format_footnotes_markdown(sections: dict, ticker: str) -> str:
    """Format parsed filing sections into readable markdown.

    Args:
        sections: Output from parse_filing_sections().
        ticker: Ticker symbol for the header.

    Returns:
        Markdown string with section headers and content.
        Empty string if no sections were found.
    """
    if not sections or not sections.get("sections"):
        return ""

    found_sections = [s for s in sections["sections"] if s.get("found")]
    if not found_sections:
        return ""

    parts: List[str] = []
    summary = sections.get("summary", {})
    parts.append(
        f"*{summary.get('found_count', 0)}/{summary.get('total_count', 0)} "
        f"sections extracted from latest filing*"
    )
    parts.append("")

    for section in found_sections:
        parts.append(f"### {section['name']} ({section['id']})")
        parts.append("")
        parts.append(section["content"])
        parts.append("")

    return "\n".join(parts)


def get_footnotes_markdown(ticker: str) -> str:
    """High-level API: download latest 10-K, parse footnotes, return markdown.

    Combines download_filing + parse_filing_sections + format_footnotes_markdown.
    The parsed sections JSON is cached on disk with a 90-day TTL so repeated
    calls for the same ticker are fast.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL').

    Returns:
        Markdown string with footnote sections.
        Empty string if EDGAR is unavailable or parsing fails.
    """
    ticker_upper = ticker.upper()

    # Check for cached parsed result
    cache_dir = _FILING_CACHE_DIR / ticker_upper
    cache_dir.mkdir(parents=True, exist_ok=True)
    parsed_cache = cache_dir / f"{ticker_upper}_filing_sections.json"

    if parsed_cache.exists():
        age_days = (time.time() - parsed_cache.stat().st_mtime) / 86400
        if age_days < _FILING_CACHE_TTL_DAYS:
            try:
                sections = json.loads(parsed_cache.read_text(encoding="utf-8"))
                if sections and sections.get("sections"):
                    logger.debug(
                        "Using cached filing sections for %s (%.0f days old)",
                        ticker_upper, age_days,
                    )
                    return format_footnotes_markdown(sections, ticker_upper)
            except (json.JSONDecodeError, OSError):
                pass  # Re-parse if cache is corrupted

    # Download the filing
    try:
        html_path = download_filing(ticker_upper, form_type="10-K")
    except Exception as e:
        logger.warning("EDGAR filing download failed for %s: %s", ticker_upper, e)
        return ""

    if html_path is None:
        return ""

    # Parse sections
    try:
        sections = parse_filing_sections(html_path)
    except Exception as e:
        logger.warning("EDGAR filing parse failed for %s: %s", ticker_upper, e)
        return ""

    if not sections:
        return ""

    # Cache the parsed result
    try:
        parsed_cache.write_text(
            json.dumps(sections, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as e:
        logger.warning("Failed to cache parsed sections for %s: %s", ticker_upper, e)

    return format_footnotes_markdown(sections, ticker_upper)
