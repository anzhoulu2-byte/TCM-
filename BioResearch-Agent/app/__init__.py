"""BioResearch-Agent Web 界面包。"""

from .prompt_generator import PromptGenerator
from .config_panel import render_config_panel, load_presets

__all__ = [
    "PromptGenerator",
    "render_config_panel",
    "load_presets",
]
