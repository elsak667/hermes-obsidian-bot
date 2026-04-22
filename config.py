"""
Hermes-Obsidian Bot 配置
"""

import os

load_dotenv()  # 加载 .env 环境变量（放在最前面）

# 飞书应用配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "cli_your_app_id")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_BOT_NAME = "Hermes"

# Obsidian Vault 路径
VAULT_PATH = os.getenv("VAULT_PATH", "/Users/els/Documents/Obsidian Vault/")

# AI API 配置
# 推荐使用 NVIDIA 免费 API（z-ai/glm4.7）
AI_PROVIDER = os.getenv("AI_PROVIDER", "nvidia")  # "anthropic", "openai", "nvidia"
AI_API_KEY = os.getenv("AI_API_KEY", "")  # Anthropic/OpenAI key
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")  # NVIDIA NGC key (免费)
AI_MODEL = os.getenv("AI_MODEL", "z-ai/glm4.7")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://integrate.api.nvidia.com/v1")

# 定时任务
WEEKLY_REPORT_CRON = "0 20 * * 0"

# Vault 目录结构
DIRS = {
    "daily": "daily/",
    "ideas": "ideas/",
    "todos": "todos/",
    "projects": "projects/",
    "weekly": "weekly/",
    "journal": "journal/",
    "inbox": "inbox/",
}

STATE_FILE = os.getenv("STATE_FILE", "/Users/els/hermes-obsidian-bot/state.json")
