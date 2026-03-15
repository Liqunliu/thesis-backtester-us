"""
引擎模块 - 策略无关的核心能力

提供 StrategyConfig、Launcher、OperatorRegistry、Tracker。
所有功能均需 StrategyConfig 驱动，不含任何策略默认值。
"""
from .config import StrategyConfig, get_default_config

__all__ = ["StrategyConfig", "get_default_config"]
