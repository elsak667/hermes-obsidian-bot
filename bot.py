"""
Hermes-Obsidian Bot
飞书消息接收 → AI 理解 → 写入 Obsidian
定时任务 → 周报生成
"""

import json
import os
import re
import sys
import datetime
import hashlib
from pathlib import Path
from typing import Optional

import pytz
from dotenv import load_dotenv
load_dotenv()
from lark_oapi import LogLevel
from lark_oapi import Client
from lark_oapi.api.im.v1 import *
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.ws.client import Client as WSClient
import lark_oapi.ws.client as ws_client_module

from config import (
    FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_BOT_NAME,
    VAULT_PATH, AI_PROVIDER, AI_API_KEY, NVIDIA_API_KEY, AI_MODEL, AI_BASE_URL, DIRS
)

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def retry(max_attempts=3, delay=1):
    """简单重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"[重试] {func.__name__} 失败 (尝试 {attempt+1}/{max_attempts}): {e}")
                    import time; time.sleep(delay)
            return None
        return wrapper
    return decorator


@retry(max_attempts=3, delay=2)
def call_nvidia_api(base_url: str, api_key: str, model: str, prompt: str, max_tokens: int = 1024) -> str:
    """调用 NVIDIA API（OpenAI 兼容格式）"""
    import httpx

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }

    resp = httpx.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def call_anthropic_api(base_url: str, api_key: str, model: str, prompt: str, max_tokens: int = 1024) -> str:
    """直接用 httpx 调用 Anthropic API"""
    import httpx

    url = f"{base_url}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }

    resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # 兼容不同响应格式
    content = data.get("content", [])
    if isinstance(content, list) and len(content) > 0:
        return content[0].get("text", str(content[0]))
    return str(content)


@retry(max_attempts=3, delay=2)
def call_openai_api(base_url: str, api_key: str, model: str, prompt: str, max_tokens: int = 1024) -> str:
    """直接用 httpx 调用 OpenAI API"""
    import httpx

    url = f"{base_url}/chat/completions"
    headers = {
        "api-key": api_key,
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }

    resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def get_vault_path(sub_dir: str, filename: str = None) -> Path:
    """获取 Vault 完整路径"""
    base = Path(VAULT_PATH)
    full_path = base / DIRS.get(sub_dir, sub_dir + "/")
    if filename:
        full_path = full_path / filename
    return full_path


def ensure_dirs():
    """确保 Vault 目录存在"""
    base = Path(VAULT_PATH)
    for d in DIRS.values():
        (base / d).mkdir(parents=True, exist_ok=True)


def detect_intent(text: str) -> str:
    """检测消息意图（无 API 时备用）"""
    text_lower = text.lower()
    keywords = {
        "todo": ["待办", "todo", "要做", "记得", "任务", "完成", "去做"],
        "reminder": ["提醒", "记得", "几点", "几点钟", "时间"],
        "idea": ["想法", "灵感", "构思", "思路", "创意", "idea"],
        "journal": ["记录", "日记", "碎碎念", "今天", "这周", "工作"],
        "project": ["项目", "需求", "功能", "改版", "计划"],
    }
    for intent, kws in keywords.items():
        for kw in kws:
            if kw in text_lower:
                return intent
    return "journal"


def parse_reminder_time(text: str) -> Optional[str]:
    """从文本中解析提醒时间"""
    patterns = [
        (r'今天(\d+)点', 0),
        (r'明天(\d+)点', 1),
        (r'周二(\d+)点', 1),
        (r'周三(\d+)点', 2),
        (r'周四(\d+)点', 3),
        (r'周五(\d+)点', 4),
        (r'周六(\d+)点', 5),
        (r'周日(\d+)点', 6),
        (r'周一(\d+)点', 7),
    ]
    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai'))
    for pattern, days_offset in patterns:
        m = re.search(pattern, text)
        if m:
            hour = int(m.group(1))
            target = now + datetime.timedelta(days=days_offset)
            target = target.replace(hour=hour, minute=0, second=0)
            return target.strftime("%Y-%m-%d %H:%M")
    return None


def ai_classify(text: str) -> dict:
    """用 AI 精准理解消息意图"""
    if not AI_API_KEY:
        return {
            "intent": detect_intent(text),
            "summary": text[:50],
            "tags": [],
            "reminder_time": parse_reminder_time(text),
            "action_items": [],
        }

    prompt = f"""你是一个意图分类助手。用户发来一条消息，请分析其意图并返回结构化结果。

消息内容：{text}

意图类型：
- todo：需要完成的任务/待办事项
- reminder：需要在特定时间提醒的事项
- idea：想法/灵感/创意
- journal：工作记录/日记/碎碎念
- project：项目相关/需求/计划

请以 JSON 格式返回：
{{
  "intent": "意图类型",
  "summary": "一句话概括核心内容",
  "tags": ["标签1", "标签2"],
  "reminder_time": "提醒时间，格式 YYYY-MM-DD HH:MM，如果没有请填 null",
  "action_items": ["可执行的待办事项列表，如果没有请填空数组"]
}}

只返回 JSON，不要有其他内容。"""

    try:
        if AI_PROVIDER == "nvidia":
            result_text = call_nvidia_api(AI_BASE_URL, NVIDIA_API_KEY, AI_MODEL, prompt)
        elif AI_PROVIDER == "anthropic":
            result_text = call_anthropic_api(AI_BASE_URL, AI_API_KEY, AI_MODEL, prompt)
        elif AI_PROVIDER == "openai":
            result_text = call_openai_api(AI_BASE_URL, AI_API_KEY, AI_MODEL, prompt)
        else:
            raise ValueError(f"不支持的 AI Provider: {AI_PROVIDER}")

        # 提取并验证 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result_text = json_match.group()
        result = json.loads(result_text)

        # 验证必要字段
        if "intent" not in result:
            raise ValueError("AI 返回缺少 intent 字段")

        return result
    except Exception as e:
        print(f"AI 分类失败: {e}")
        return {
            "intent": detect_intent(text),
            "summary": text[:50],
            "tags": [],
            "reminder_time": parse_reminder_time(text),
            "action_items": [],
        }


def save_to_obsidian(intent: str, text: str, ai_result: dict) -> str:
    """根据意图保存到 Obsidian"""
    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai'))
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    filename_date = now.strftime("%Y%m%d")
    unique_id = hashlib.md5(f"{text}{time_str}".encode()).hexdigest()[:6]

    # 构建内容
    content_lines = [
        f"# {ai_result.get('summary', text[:30])}",
        "",
        f"**原文**: {text}",
        f"**时间**: {date_str} {time_str}",
        f"**意图**: {intent}",
    ]

    if ai_result.get("tags"):
        content_lines.append(f"**标签**: {' / '.join(ai_result['tags'])}")

    if ai_result.get("action_items"):
        content_lines.append("")
        content_lines.append("## 待办")
        for item in ai_result["action_items"]:
            content_lines.append(f"- [ ] {item}")

    if ai_result.get("reminder_time"):
        content_lines.append("")
        content_lines.append(f"**提醒时间**: {ai_result['reminder_time']}")

    content_lines.append("")
    content_lines.append("---")
    content_lines.append(f"**存入**: {datetime.datetime.now().isoformat()}")

    content = "\n".join(content_lines)
    saved_path = None

    # 根据意图写入对应目录
    if intent == "idea":
        target_path = get_vault_path("ideas", f"{filename_date}_{unique_id}.md")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        saved_path = str(target_path)

    elif intent == "todo":
        target_path = get_vault_path("todos", f"{filename_date}_{unique_id}.md")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        saved_path = str(target_path)

    elif intent == "project":
        target_path = get_vault_path("projects", f"{filename_date}_{unique_id}.md")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        saved_path = str(target_path)

    # 追加到每日笔记
    daily_path = get_vault_path("daily", f"{date_str}.md")
    daily_path.parent.mkdir(parents=True, exist_ok=True)

    existing = ""
    if daily_path.exists():
        existing = daily_path.read_text(encoding="utf-8")

    new_entry = f"\n\n## {time_str} [{intent}] {ai_result.get('summary', text[:20])}"
    new_entry += f"\n{text}"

    if daily_path.exists():
        daily_path.write_text(existing + new_entry, encoding="utf-8")
    else:
        daily_path.write_text(f"# {date_str}\n{new_entry}", encoding="utf-8")

    return saved_path or str(daily_path)


def generate_weekly_report() -> str:
    """生成周报"""
    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai'))
    monday = now - datetime.timedelta(days=now.weekday())
    week_str = now.strftime("%Y-W%W")
    report_path = get_vault_path("weekly", f"{week_str}.md")

    # 收集本周每日笔记
    daily_notes = []
    for i in range(7):
        day = monday + datetime.timedelta(days=i)
        day_file = get_vault_path("daily", f"{day.strftime('%Y-%m-%d')}.md")
        if day_file.exists():
            daily_notes.append({
                "date": day.strftime("%Y-%m-%d"),
                "content": day_file.read_text(encoding="utf-8")
            })

    # 用 AI 生成周报
    if AI_API_KEY and daily_notes:
        context = "\n\n".join([f"### {n['date']}\n{n['content'][:800]}" for n in daily_notes])

        prompt = f"""根据以下每日笔记，生成一份周报：

{context}

周报格式：
# {week_str} 周报

## 本周完成
-

## 进行中
-

## 灵感/想法
-

## 下周计划
-

请简洁地总结，不要废话。"""

        try:
            if AI_PROVIDER == "nvidia":
                report_content = call_nvidia_api(AI_BASE_URL, NVIDIA_API_KEY, AI_MODEL, prompt, max_tokens=2048)
            elif AI_PROVIDER == "anthropic":
                report_content = call_anthropic_api(AI_BASE_URL, AI_API_KEY, AI_MODEL, prompt, max_tokens=2048)
            elif AI_PROVIDER == "openai":
                report_content = call_openai_api(AI_BASE_URL, AI_API_KEY, AI_MODEL, prompt, max_tokens=2048)
        except Exception as e:
            report_content = f"# {week_str} 周报\n\n生成失败: {e}"
    else:
        report_content = f"# {week_str} 周报\n\n（请手动补充本周内容）"

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_content, encoding="utf-8")

    return str(report_path)


def build_reply_text(intent: str, ai_result: dict, saved_path: str = None) -> str:
    """构建回复文本"""
    path_tip = f"\n📄 {saved_path}" if saved_path else ""

    reply_map = {
        "todo": f"✅ 已记为待办{path_tip}",
        "reminder": f"⏰ 提醒已设置（{ai_result.get('reminder_time', '时间待定')}）",
        "idea": f"💡 灵感已存入 ideas{path_tip}",
        "journal": f"📝 已存入今日笔记{path_tip}",
        "project": f"📁 已存入项目笔记{path_tip}",
        "weekly_report": f"📊 周报已生成{path_tip}",
        "view_weekly": f"📊 最新周报{path_tip}",
    }
    return reply_map.get(intent, f"📥 已收到{path_tip}")


# 创建飞书 API 客户端（用于发送消息）
feishu_client: Optional[Client] = None

# 存储状态
user_chat_id: Optional[str] = None
user_open_id: Optional[str] = None

def get_feishu_client() -> Client:
    global feishu_client
    if feishu_client is None:
        feishu_client = (
            Client.builder()
            .app_id(FEISHU_APP_ID)
            .app_secret(FEISHU_APP_SECRET)
            .log_level(LogLevel.WARNING)
            .build()
        )
    return feishu_client


def send_reply(message_id: str, text: str):
    """发送回复消息"""
    try:
        client = get_feishu_client()
        content = json.dumps({"text": text})

        request = (
            ReplyMessageRequest.builder()
            .message_id(message_id)
            .request_body(
                ReplyMessageRequestBody.builder()
                .content(content)
                .msg_type("text")
                .build()
            )
            .build()
        )

        client.im.v1.message.reply(request)

    except Exception as e:
        print(f"发送回复失败: {e}")


def send_to_user(text: str):
    """主动推送消息给用户（使用已记录的 chat_id）"""
    global user_chat_id
    if not user_chat_id:
        print("没有记录用户的 chat_id，无法主动发送")
        return

    try:
        client = get_feishu_client()
        content = json.dumps({"text": text})

        request = (
            CreateMessageRequest.builder()
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(user_chat_id)
                .receive_id_type("chat_id")
                .msg_type("text")
                .content(content)
                .build()
            )
            .build()
        )

        client.im.v1.message.create(request)
        print(f"已推送消息到用户: {text[:30]}...")

    except Exception as e:
        print(f"推送失败: {e}")


def save_state():
    """保存状态到文件"""
    import json
    state = {"user_chat_id": user_chat_id, "user_open_id": user_open_id}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def load_state():
    """从文件加载状态"""
    import json
    global user_chat_id, user_open_id
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                user_chat_id = state.get("user_chat_id")
                user_open_id = state.get("user_open_id")
        except Exception as e:
            print(f"加载状态失败: {e}")


def on_message_receive(data: P2ImMessageReceiveV1):
    """收到消息的处理函数"""
    global user_chat_id
    print(f"[DEBUG] 收到事件: {data}")
    try:
        message = data.event.message
        text = ""
        if hasattr(message, 'content') and message.content:
            try:
                content_obj = json.loads(message.content)
                text = content_obj.get('text', '')
            except:
                text = str(message.content)

        if not text:
            return

        # 特殊指令：查看周报
        if text.strip() in ["查看周报", "周报", "看周报"]:
            import glob
            weekly_dir = get_vault_path("weekly")
            reports = sorted(weekly_dir.glob("*.md"), key=lambda p: p.name, reverse=True)
            if reports:
                latest = reports[0]
                reply_text = f"📊 最新周报：{latest.name}\n📄 {latest}"
            else:
                reply_text = "📊 暂无周报，请先让我记录一些内容"
            send_reply(message.message_id, reply_text)
            return

        # 记录 chat_id 和 open_id（用于后续主动推送）
        chat_id = getattr(message, 'chat_id', None)
        open_id = getattr(data.event.sender.sender_id, 'open_id', None)
        if chat_id:
            user_chat_id = chat_id
        if open_id:
            user_open_id = open_id
            save_state()
            print(f"已记录 open_id: {user_open_id}")

        print(f"[{data.event.sender.sender_id.user_id}] {text}")
        print(f"[DEBUG] sender_id open_id: {data.event.sender.sender_id.open_id}")
        print(f"[DEBUG] chat_id: {getattr(message, 'chat_id', None)}")

        # AI 理解
        ai_result = ai_classify(text)
        intent = ai_result["intent"]

        # 保存到 Obsidian
        saved_path = save_to_obsidian(intent, text, ai_result)

        # 回复
        reply_text = build_reply_text(intent, ai_result)
        send_reply(message.message_id, reply_text)

        print(f"完成: {intent} → {saved_path}")

    except Exception as e:
        print(f"处理消息失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("=" * 50)
    print("Hermes-Obsidian Bot 启动中...")
    print("=" * 50)

    ensure_dirs()
    load_state()

    print(f"飞书应用: {FEISHU_APP_ID}")
    print(f"Vault: {VAULT_PATH}")
    print(f"AI: {AI_PROVIDER} / {AI_MODEL}")
    print("=" * 50)

    # 构建事件处理器
    handler = (
        EventDispatcherHandler.builder(encrypt_key="", verification_token="")
        .register_p2_im_message_receive_v1(on_message_receive)
        .build()
    )
    print("[INFO] handler 注册完成, keys: {list(handler._processorMap.keys())}")

    # 定时任务：每周日 20:00 生成周报
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Shanghai'))
    scheduler.add_job(
        generate_weekly_report,
        CronTrigger(day_of_week='sun', hour=20, minute=0, timezone='Asia/Shanghai'),
        id='weekly_report'
    )
    scheduler.start()
    print("[INFO] 定时任务已启动: 每周日 20:00 生成周报")

    # 启动 WebSocket 长连接（阻塞）
    ws_client = WSClient(
        app_id=FEISHU_APP_ID,
        app_secret=FEISHU_APP_SECRET,
        event_handler=handler,
    )

    print("等待飞书消息...")
    ws_client.start()


if __name__ == "__main__":
    main()
