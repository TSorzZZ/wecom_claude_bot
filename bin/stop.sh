#!/bin/bash
# 企业微信 Claude Bot 停止脚本
# 由 Claude Code SessionEnd hook 自动调用

BOT_DIR="${CLAUDE_PLUGIN_ROOT}"
PID_FILE="$BOT_DIR/.bot.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm -f "$PID_FILE"
        echo "[wecom-bot] 已停止 (PID=$PID)"
    else
        rm -f "$PID_FILE"
        echo "[wecom-bot] 进程已不存在，清理 PID 文件"
    fi
else
    echo "[wecom-bot] 未找到 PID 文件，可能未运行"
fi
