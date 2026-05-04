"""
苹果提醒事项接入模块
依赖: brew install steipete/tap/remindctl
"""

import subprocess
import re
from typing import Optional


def add_reminder(
    title: str,
    due_date: str = None,
    list_name: str = "提醒",
) -> dict:
    """
    在苹果提醒事项里创建一个待办

    参数:
        title: 提醒内容
        due_date: 到期时间，格式 "YYYY-MM-DD" 或 "YYYY-MM-DD HH:mm"（可选）
        list_name: 列表名称，默认 "提醒"

    返回:
        {"success": bool, "output": str}
    """
    cmd = ["remindctl", "add", "--title", title, "--list", list_name]
    if due_date:
        cmd += ["--due", due_date]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return {"success": True, "output": result.stdout.strip()}
        else:
            return {"success": False, "output": result.stderr.strip()}
    except Exception as e:
        return {"success": False, "output": str(e)}


def list_reminders(list_name: str = None) -> dict:
    """查看提醒列表"""
    cmd = ["remindctl"] + (["list", list_name] if list_name else ["all"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return {"success": True, "output": result.stdout.strip()}
    except Exception as e:
        return {"success": False, "output": str(e)}


# ---- 测试 ----
if __name__ == "__main__":
    # 测试：不带日期
    r1 = add_reminder("测试提醒：无日期")
    print("无日期:", r1)

    # 测试：带日期（明天）
    import datetime
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    r2 = add_reminder("测试提醒：带日期", due_date=f"{tomorrow} 09:00")
    print("带日期:", r2)

    # 列出所有
    r3 = list_reminders()
    print("列表:", r3)
