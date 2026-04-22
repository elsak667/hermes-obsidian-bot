"""
Hermes-Obsidian Bot 配置示例
复制为 config_local.py 并填入真实值
"""

# 飞书应用配置
FEISHU_APP_ID = "cli_xxxxxxxx"
FEISHU_APP_SECRET = "your_feishu_app_secret_here"
FEISHU_BOT_NAME = "Hermes"

# Obsidian Vault 路径
VAULT_PATH = "/Users/els/Documents/Obsidian Vault/"

# AI API 配置
AI_PROVIDER = "anthropic"  # "anthropic" 或 "openai"
AI_API_KEY = "your_api_key_here"
AI_MODEL = "claude-sonnet-4-7-2025-06-09"
AI_BASE_URL = "https://api.nengpa.com/anthropic"

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

STATE_FILE = "/Users/els/hermes-obsidian-bot/state.json"
