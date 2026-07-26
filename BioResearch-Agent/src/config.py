"""
BioResearch-Agent 配置文件。

使用 pydantic-settings 从 .env 文件加载配置项，
通过 Config 单例类提供统一的全局配置访问接口。
"""

from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 加载 .env 文件（如果存在）
env_file = _PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)


class Config(BaseSettings):
    """应用全局配置单例。

    从 .env 文件和环境变量中读取配置，提供类型安全的配置访问。
    配置项的默认值确保缺少 .env 文件时仍可运行。
    """

    # ── 应用信息 ──────────────────────────────────
    app_name: str = "BioResearch-Agent"
    """应用名称"""
    app_version: str = "1.0.0"
    """应用版本号"""

    # ── 日志配置 ──────────────────────────────────
    log_level: str = "INFO"
    """日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL"""

    # ── API 密钥 ──────────────────────────────────
    deepseek_api_key: str = ""
    """DeepSeek API 密钥"""
    openai_api_key: str = ""
    """OpenAI API 密钥"""

    # ── PubMed 配置 ───────────────────────────────
    pubmed_email: str = ""
    """PubMed E-utilities 请求邮箱（NCBI 要求提供）"""

    # ── 路径配置 ──────────────────────────────────
    data_dir: str = str(_PROJECT_ROOT / "data")
    """数据文件目录"""
    output_dir: str = str(_PROJECT_ROOT / "outputs")
    """输出文件目录"""

    # ── 请求与超时配置 ────────────────────────────
    request_timeout: int = 60
    """HTTP 请求超时时间（秒）"""
    max_retries: int = 3
    """HTTP 请求最大重试次数"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,  # 配置项不可变
    )


@lru_cache(maxsize=1)
def get_config() -> Config:
    """获取 Config 单例。

    使用 lru_cache 确保全局只创建一次 Config 实例，
    所有模块通过此函数共享同一份配置。

    Returns:
        Config: 全局配置单例
    """
    return Config()
