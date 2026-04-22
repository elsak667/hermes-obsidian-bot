"""
Heremes-Obsidian Bot 配置
"""

# 飞书应用配置
FEISHU_APP_ID = "cli_a96201337ff8dcbc"
FEISHU_APP_SECRET = "8Uu1nBf2EGk5KAEwpgwHZeSVXf4M3g71"
FEISHU_BOT_NAME = "Hermes"

# Obsidian Vault 路径
VAULT_PATH = "/Users/els/Documents/Obsidian Vault/"

# AI API 配置
# 支持 Anthropic 或 OpenAI
AI_PROVIDER = "anthropic"  # "anthropic" 或 "openai"
AI_API_KEY = "sk-cp-26454c4264289bb38b24ea18ff78f9a9e430636175221d063b1534e049d41fb3"
AI_MODEL = "claude-sonnet-4-7-2025-06-09"  # Anthropic 模型

# AI API Base URL（使用代理或自定义端点时填写）
AI_BASE_URL = "https://api.nengpa.com/anthropic"

# 定时任务
# 周报生成时间：每周日 20:00
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

# 状态存储（chat_id 等）
STATE_FILE = "/Users/els/hermes-obsidian-bot/state.json"
