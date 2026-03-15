"""
全局配置

环境变量:
    TUSHARE_TOKEN    Tushare Pro API token (必需)
    DATA_PROVIDER    数据源名称 (默认 "tushare")

路径常量:
    TUSHARE_DATA_DIR    市场数据目录  data/tushare/
    FINANCIAL_DATA_DIR  财报数据目录  data/financial/
    SNAPSHOT_DIR        快照输出目录  data/snapshots/
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = PROJECT_ROOT / "data"

# 加载 .env 文件（如果存在）
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# Tushare 配置
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")

# 数据目录
TUSHARE_DATA_DIR = DATA_ROOT / "tushare"
FINANCIAL_DATA_DIR = DATA_ROOT / "financial"
SNAPSHOT_DIR = DATA_ROOT / "snapshots"
ANALYSIS_DB_PATH = DATA_ROOT / "analysis_results" / "results.db"

# Parquet 压缩方式
PARQUET_COMPRESSION = "zstd"

# 数据提供者 (tushare / akshare / csv / ...)
DATA_PROVIDER = os.environ.get("DATA_PROVIDER", "tushare")

# 日期格式
DATE_FORMAT = "%Y-%m-%d"

# 数据起始日期 (回填下限)
DATA_START_DATE = os.environ.get("DATA_START_DATE", "2015-01-01")
