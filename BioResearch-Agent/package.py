"""
BioResearch-Agent 打包发布脚本。

使用方式:
    python package.py sdist          # 构建源码分发包
    python package.py wheel          # 构建 wheel 分发包
    python package.py publish        # 发布到 PyPI（需 twine）
    python package.py install        # 安装到当前环境
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PKG_NAME = "bioresearch-agent"
VERSION = "1.0.0"
AUTHOR = "BioResearch-Agent Team"
AUTHOR_EMAIL = "team@bioresearch-agent.dev"
DESCRIPTION = "AI-driven biomedical research automation platform"
LICENSE = "MIT"
PYTHON_REQUIRES = ">=3.10"


def build_sdist() -> None:
    """构建源码分发包。"""
    print("📦 构建源码分发包 (sdist)...")
    subprocess.check_call(
        [sys.executable, "-m", "build", "--sdist", str(HERE)],
        cwd=HERE,
    )
    dist_dir = HERE / "dist"
    sdist_files = list(dist_dir.glob("*.tar.gz"))
    if sdist_files:
        print(f"✅ 构建成功: {sdist_files[0].name}")
    else:
        print("❌ 构建失败")


def build_wheel() -> None:
    """构建 wheel 分发包。"""
    print("📦 构建 wheel 分发包...")
    subprocess.check_call(
        [sys.executable, "-m", "build", "--wheel", str(HERE)],
        cwd=HERE,
    )
    dist_dir = HERE / "dist"
    wheel_files = list(dist_dir.glob("*.whl"))
    if wheel_files:
        print(f"✅ 构建成功: {wheel_files[0].name}")
    else:
        print("❌ 构建失败")


def publish() -> None:
    """发布到 PyPI。"""
    print("📤 发布到 PyPI...")
    subprocess.check_call(
        [sys.executable, "-m", "twine", "upload", "dist/*"],
        cwd=HERE,
    )
    print("✅ 发布成功")


def install_local() -> None:
    """安装到当前环境。"""
    print("📥 安装到当前环境...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-e", str(HERE)],
        cwd=HERE,
    )
    print("✅ 安装成功")


def ensure_build_deps() -> None:
    """确保构建依赖已安装。"""
    deps = ["build", "twine", "wheel", "setuptools"]
    for dep in deps:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", dep],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def write_setup_cfg() -> None:
    """生成 setup.cfg / pyproject.toml 配置。"""
    pyproject = HERE / "pyproject.toml"
    if not pyproject.exists():
        print("📝 生成 pyproject.toml...")
        pyproject.write_text(f"""\
[build-system]
requires = ["setuptools>=68.0", "wheel>=0.41"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "{PKG_NAME}"
version = "{VERSION}"
description = "{DESCRIPTION}"
readme = "README.md"
license = "{{text = \\"{LICENSE}\\"}}"
authors = [
    {{name = "{AUTHOR}", email = "{AUTHOR_EMAIL}"}},
]
requires-python = "{PYTHON_REQUIRES}"
dependencies = [
    "requests>=2.31.0",
    "httpx>=0.27.0",
    "aiohttp>=3.14.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "pandas>=2.1.0",
    "numpy>=1.26.0",
    "matplotlib>=3.8.0",
    "seaborn>=0.13.0",
    "scipy>=1.11.0",
    "loguru>=0.7.2",
    "python-docx>=0.8.11",
    "streamlit>=1.31.0",
    "plotly>=5.18.0",
]

[project.urls]
"Homepage" = "https://github.com/your-org/bioresearch-agent"
"Bug Tracker" = "https://github.com/your-org/bioresearch-agent/issues"

[project.scripts]
bioresearch-agent = "src.main:main"

[tool.setuptools.packages.find]
where = ["src", "app"]
include = ["src*", "app*"]
""")


def main() -> None:
    """主入口。"""
    if len(sys.argv) < 2:
        print(f"用法: python {Path(__file__).name} [sdist|wheel|publish|install|all]")
        print()
        print("   sdist     构建源码分发包")
        print("   wheel     构建 wheel 分发包")
        print("   publish   发布到 PyPI")
        print("   install   安装到当前环境")
        print("   all       构建 sdist + wheel")
        sys.exit(0)

    ensure_build_deps()
    write_setup_cfg()

    command = sys.argv[1]
    if command == "sdist":
        build_sdist()
    elif command == "wheel":
        build_wheel()
    elif command == "publish":
        build_sdist()
        build_wheel()
        publish()
    elif command == "install":
        install_local()
    elif command == "all":
        build_sdist()
        build_wheel()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
