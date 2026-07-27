#!/usr/bin/env python3
"""BioResearch-Agent API 启动入口。

用法:
    python run_api.py
    python run_api.py --port 8510 --host 0.0.0.0
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_project_root))

import argparse
from src.api import main as api_main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BioResearch-Agent API 服务器")
    parser.add_argument("--port", type=int, default=8510, help="监听端口 (默认 8510)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址 (默认 0.0.0.0)")
    args = parser.parse_args()

    # 覆盖端口配置
    import uvicorn
    from loguru import logger

    logger.info(f"API 服务器启动: http://{args.host}:{args.port}")
    logger.info(f"API 文档: http://{args.host}:{args.port}/api/docs")
    logger.info(f"健康检查: http://{args.host}:{args.port}/api/health")

    uvicorn.run(
        "src.api:app",
        host=args.host,
        port=args.port,
        reload=True,
        log_level="info",
    )
