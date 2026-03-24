#!/bin/bash
# 企业微信 Claude Bot 启动脚本
# 由 Claude Code SessionStart hook 自动调用

BOT_DIR="${CLAUDE_PLUGIN_ROOT}"
PID_FILE="$BOT_DIR/.bot.pid"
LOG_FILE="$BOT_DIR/.bot.log"

# 检查是否已在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[wecom-bot] 已在运行 (PID=$PID)"
        exit 0
    fi
fi

# 启动 bot
cd "$BOT_DIR"
nohup python3 main.py >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "[wecom-bot] 已启动 (PID=$(cat $PID_FILE))"
