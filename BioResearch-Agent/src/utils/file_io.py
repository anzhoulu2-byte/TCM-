"""
文件输入/输出工具模块。

提供文件读写、目录管理、格式转换等实用函数。
"""

import json
import csv
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger


class FileIO:
    """文件读写工具类。"""

    @staticmethod
    def ensure_dir(path: str | Path) -> Path:
        """确保目录存在，如果不存在则创建。

        Args:
            path: 目录路径

        Returns:
            Path 对象
        """
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def read_text(file_path: str | Path, encoding: str = "utf-8") -> str:
        """读取文本文件。

        Args:
            file_path: 文件路径
            encoding: 文件编码

        Returns:
            文件内容字符串
        """
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()

    @staticmethod
    def write_text(file_path: str | Path, content: str, encoding: str = "utf-8") -> None:
        """写入文本文件。

        Args:
            file_path: 文件路径
            content: 内容
            encoding: 文件编码
        """
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding=encoding) as f:
            f.write(content)
        logger.debug(f"写入文件: {p}")

    @staticmethod
    def read_json(file_path: str | Path) -> dict | list:
        """读取 JSON 文件。

        Args:
            file_path: 文件路径

        Returns:
            解析后的 JSON 数据
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def write_json(file_path: str | Path, data: Any, indent: int = 2) -> None:
        """写入 JSON 文件。

        Args:
            file_path: 文件路径
            data: 数据
            indent: 缩进空格数
        """
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        logger.debug(f"写入 JSON 文件: {p}")

    @staticmethod
    def read_csv(file_path: str | Path, **kwargs) -> pd.DataFrame:
        """读取 CSV 文件为 DataFrame。

        Args:
            file_path: 文件路径
            **kwargs: 传递给 pandas.read_csv 的参数

        Returns:
            pandas DataFrame
        """
        return pd.read_csv(file_path, **kwargs)

    @staticmethod
    def write_csv(
        file_path: str | Path,
        data: pd.DataFrame | list[dict],
        index: bool = False,
        **kwargs,
    ) -> None:
        """写入 CSV 文件。

        Args:
            file_path: 文件路径
            data: DataFrame 或 dict 列表
            index: 是否写入行索引
            **kwargs: 传递给 pandas.to_csv 的参数
        """
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, list):
            data = pd.DataFrame(data)

        data.to_csv(p, index=index, encoding="utf-8-sig", **kwargs)
        logger.debug(f"写入 CSV 文件: {p}")

    @staticmethod
    def read_fasta(file_path: str | Path) -> dict[str, str]:
        """读取 FASTA 格式文件。

        Args:
            file_path: 文件路径

        Returns:
            字典，key 为序列 ID，value 为序列
        """
        sequences: dict[str, str] = {}
        current_id: str | None = None
        current_seq: list[str] = []

        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if current_id:
                        sequences[current_id] = "".join(current_seq)
                    current_id = line[1:].split()[0]
                    current_seq = []
                elif current_id:
                    current_seq.append(line)

        if current_id:
            sequences[current_id] = "".join(current_seq)

        return sequences

    @staticmethod
    def list_files(
        directory: str | Path,
        pattern: str = "*",
        recursive: bool = False,
    ) -> list[Path]:
        """列出目录中的文件。

        Args:
            directory: 目录路径
            pattern: 通配符模式
            recursive: 是否递归搜索子目录

        Returns:
            文件路径列表
        """
        p = Path(directory)
        if not p.exists():
            logger.warning(f"目录不存在: {p}")
            return []

        if recursive:
            return list(p.rglob(pattern))
        return list(p.glob(pattern))
