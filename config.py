"""
Hermes-Obsidian Bot 配置
"""

import os

# 飞书应用配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "cli_your_app_id")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_BOT_NAME = "Hermes"

# Obsidian Vault 路径
VAULT_PATH = os.getenv("VAULT_PATH", "/Users/els/Documents/Obsidian Vault/")

# AI API 配置
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-7-2025-06-09")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.nengpa.com/anthropic")

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
