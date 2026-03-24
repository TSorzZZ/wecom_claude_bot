#!/bin/bash
# 企业微信 Claude Bot 安装脚本
# 用法：bash install.sh

set -e

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$BOT_DIR/.env"
ENV_EXAMPLE="$BOT_DIR/.env.example"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   企业微信 × Claude Code Bot  安装向导   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. 检查 Python ────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.10+"
    exit 1
fi
echo "✅ Python: $(python3 --version)"

# ── 2. 安装依赖 ───────────────────────────────────────────────────────────────
echo ""
echo "📦 安装 Python 依赖..."
pip3 install -q -r "$BOT_DIR/requirements.txt"
echo "✅ 依赖安装完成"

# ── 3. 如果 .env 已存在，询问是否覆盖 ─────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    echo ""
    read -r -p "⚠️  .env 已存在，是否重新配置？[y/N] " overwrite
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        echo "跳过配置，使用现有 .env"
        echo ""
        echo "✅ 安装完成！重新打开 Claude Code 即可自动启动机器人。"
        exit 0
    fi
fi

echo ""
echo "📝 开始配置（直接回车使用默认值）"
echo "──────────────────────────────────────────"

# ── 4. 企业微信配置 ───────────────────────────────────────────────────────────
echo ""
echo "【企业微信智能机器人】"
echo "  前往「企业微信管理后台 → 应用 → 智能机器人 → API配置 → 使用长连接」获取"
echo ""
read -r -p "  WECOM_BOT_ID: " wecom_bot_id
while [ -z "$wecom_bot_id" ]; do
    echo "  ❌ WECOM_BOT_ID 不能为空"
    read -r -p "  WECOM_BOT_ID: " wecom_bot_id
done

read -r -p "  WECOM_SECRET: " wecom_secret
while [ -z "$wecom_secret" ]; do
    echo "  ❌ WECOM_SECRET 不能为空"
    read -r -p "  WECOM_SECRET: " wecom_secret
done

# ── 5. Anthropic / codebuddy 配置 ─────────────────────────────────────────────
echo ""
echo "【Anthropic API 配置】"
echo "  腾讯内网（codebuddy）用户：直接回车，token 由 claude-internal 运行时自动注入"
echo "  公网用户：填入 sk-ant-xxx 格式的 API Key"
echo ""
read -r -p "  ANTHROPIC_API_KEY [留空=自动注入]: " anthropic_api_key

read -r -p "  ANTHROPIC_BASE_URL [留空=公网]: " anthropic_base_url

# ── 6. 模型 ───────────────────────────────────────────────────────────────────
echo ""
echo "【模型配置】"
read -r -p "  CLAUDE_MODEL [claude-sonnet-4-6]: " claude_model
claude_model="${claude_model:-claude-sonnet-4-6}"

# ── 7. Agent 工作目录 ─────────────────────────────────────────────────────────
echo ""
echo "【Claude Agent 配置】"
default_cwd="$(pwd)"
read -r -p "  AGENT_CWD [${default_cwd}]: " agent_cwd
agent_cwd="${agent_cwd:-$default_cwd}"

# claude-internal 路径自动检测
cli_path="$(command -v claude-internal 2>/dev/null || true)"
if [ -n "$cli_path" ]; then
    echo "  🔍 自动检测到 claude-internal: $cli_path"
    read -r -p "  AGENT_CLI_PATH [${cli_path}]: " agent_cli_path
    agent_cli_path="${agent_cli_path:-$cli_path}"
else
    read -r -p "  AGENT_CLI_PATH [留空=自动检测]: " agent_cli_path
fi

# ── 8. 写入 .env ──────────────────────────────────────────────────────────────
cat > "$ENV_FILE" <<EOF
# ── Anthropic（由 install.sh 生成）──────────────────────────────────────────
# token 由 claude-internal 运行时动态注入，此处留空时自动使用运行时 token
ANTHROPIC_API_KEY=${anthropic_api_key}
ANTHROPIC_BASE_URL=${anthropic_base_url}

# 模型
CLAUDE_MODEL=${claude_model}
CLAUDE_MAX_TOKENS=2048
SYSTEM_PROMPT=你是一个企业内部的 AI 助手，请用简洁、专业的中文回答用户问题。

# 每个用户保留的最近对话轮数
CONVERSATION_MAX_PAIRS=10

# ── 企业微信智能机器人（长连接模式）────────────────────────────────────────
WECOM_BOT_ID=${wecom_bot_id}
WECOM_SECRET=${wecom_secret}

# ── Claude Agent SDK ────────────────────────────────────────────────────────
AGENT_CWD=${agent_cwd}
AGENT_ALLOWED_TOOLS=Read,Write,Edit,Bash,Glob,Grep,WebSearch,WebFetch
AGENT_CLI_PATH=${agent_cli_path}
EOF

echo ""
echo "✅ .env 已生成：$ENV_FILE"

# ── 9. 注册插件 ───────────────────────────────────────────────────────────────
echo ""
echo "📌 注册 Claude Code 插件..."

INSTALLED_PLUGINS="${CLAUDE_CONFIG_DIR:-$HOME/.claude-internal}/plugins/installed_plugins.json"
SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude-internal}/settings.json"

if [ -f "$INSTALLED_PLUGINS" ]; then
    python3 - <<PYEOF
import json, sys, os
from datetime import datetime

path = "$INSTALLED_PLUGINS"
with open(path) as f:
    data = json.load(f)

key = "wecom-claude-bot@local"
data.setdefault("plugins", {})[key] = [{
    "scope": "user",
    "installPath": "$BOT_DIR",
    "version": "1.0.0",
    "installedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    "lastUpdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
}]

with open(path, "w") as f:
    json.dump(data, f, indent=4)

print("  ✅ installed_plugins.json 已更新")
PYEOF
else
    echo "  ⚠️  未找到 installed_plugins.json，请手动注册插件"
fi

if [ -f "$SETTINGS" ]; then
    python3 - <<PYEOF
import json

path = "$SETTINGS"
with open(path) as f:
    data = json.load(f)

data.setdefault("enabledPlugins", {})["wecom-claude-bot@local"] = True

with open(path, "w") as f:
    json.dump(data, f, indent=4)

print("  ✅ settings.json enabledPlugins 已更新")
PYEOF
else
    echo "  ⚠️  未找到 settings.json，请手动添加 enabledPlugins"
fi

# ── 10. 完成 ──────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║            🎉 安装完成！                 ║"
echo "║  重新打开 Claude Code 机器人自动上线     ║"
echo "║  日志：$BOT_DIR/.bot.log"
echo "╚══════════════════════════════════════════╝"
echo ""
