#!/bin/bash
# Hermes-Obsidian-Bot 服务管理脚本

PLIST="$HOME/Library/LaunchAgents/com.els.hermes-obsidian-bot.plist"
LABEL="com.els.hermes-obsidian-bot"

start() {
    launchctl load "$PLIST"
    echo "服务已启动"
}

stop() {
    launchctl unload "$PLIST"
    echo "服务已停止"
}

restart() {
    launchctl unload "$PLIST" 2>/dev/null
    sleep 1
    launchctl load "$PLIST"
    echo "服务已重启"
}

status() {
    if launchctl list | grep -q "$LABEL"; then
        echo "服务运行中"
    else
        echo "服务未运行"
    fi
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
