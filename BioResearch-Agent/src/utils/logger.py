"""
日志配置模块。

基于 Loguru 提供统一的日志记录接口。
"""

import sys
from pathlib import Path

from loguru import logger


def setup_logger(
    level: str = "INFO",
    log_file: str | None = None,
    rotation: str = "10 MB",
    retention: str = "30 days",
) -> None:
    """配置全局日志器。

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，为 None 时仅输出到控制台
        rotation: 日志轮转大小
        retention: 日志保留时间
    """
    # 移除默认的 sink
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
        enqueue=True,
    )

    # 文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_path),
            level=level,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                "{name}:{function}:{line} - {message}"
            ),
            rotation=rotation,
            retention=retention,
            compression="gz",
            enqueue=True,
        )

    logger.info(f"日志系统初始化完成，级别: {level}")


# 导出 logger 实例
__all__ = ["logger", "setup_logger"]
