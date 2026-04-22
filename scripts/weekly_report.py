"""
生成周报并推送
"""
import sys
sys.path.insert(0, '/Users/els/hermes-obsidian-bot')

from bot import generate_weekly_report, get_feishu_client
import json
import os

# 加载状态
state_file = "/Users/els/hermes-obsidian-bot/state.json"
if os.path.exists(state_file):
    with open(state_file) as f:
        saved_state = json.load(f)
        chat_id = saved_state.get("user_chat_id")
        open_id = saved_state.get("user_open_id")
else:
    chat_id = None
    open_id = None

print(f"open_id from state: {open_id}")

# 生成周报
report_path = generate_weekly_report()
print(f"周报已生成: {report_path}")

# 读取周报内容
with open(report_path) as f:
    raw_content = f.read()

# 过滤 thinking blocks
import re
content = re.sub(r'\{[^{]*"thinking":.*?\}(,|\s)*', '', raw_content).strip()
print(f"周报内容长度: {len(content)}")

# 推送到飞书
if open_id:
    try:
        client = get_feishu_client()
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

        msg_type = "text"
        msg_content = json.dumps({"text": f"📊 周报已生成\n\n{content[:1000]}"})
        body = (
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type(msg_type)
            .content(msg_content)
            .build()
        )
        request = (
            CreateMessageRequest.builder()
            .request_body(body)
            .receive_id_type("open_id")
            .build()
        )
        resp = client.im.v1.message.create(request)
        print(f"推送结果: code={resp.__dict__.get('code')} msg={resp.__dict__.get('msg')}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"推送失败: {e}")
elif chat_id:
    print("有 chat_id 但没有 open_id，跳过推送")
else:
    print("没有 open_id，跳过推送")

print("done")