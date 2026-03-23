"""环境变量配置（长连接版本）"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Anthropic ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "")  # 腾讯内部代理地址
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")
CLAUDE_MAX_TOKENS: int = int(os.getenv("CLAUDE_MAX_TOKENS", "2048"))
SYSTEM_PROMPT: str = os.getenv(
    "SYSTEM_PROMPT",
    "你是一个企业内部的 AI 助手，请用简洁、专业的中文回答用户问题。",
)

# ── 企业微信智能机器人（长连接模式）────────────────────────────────────────
# 在「创建智能机器人 → API配置 → 使用长连接」页面获取
WECOM_BOT_ID: str = os.environ["WECOM_BOT_ID"]
WECOM_SECRET: str = os.environ["WECOM_SECRET"]

# ── 对话历史（已弃用，SDK 内部管理 session）────────────────────────────────
CONVERSATION_MAX_PAIRS: int = int(os.getenv("CONVERSATION_MAX_PAIRS", "10"))

# ── Claude Agent SDK ────────────────────────────────────────────────────────
AGENT_CWD: str = os.getenv("AGENT_CWD", "F:/workspace")
AGENT_ALLOWED_TOOLS: list[str] = os.getenv(
    "AGENT_ALLOWED_TOOLS",
    "Read,Write,Edit,Bash,Glob,Grep,WebSearch,WebFetch",
).split(",")
AGENT_CLI_PATH: str | None = os.getenv("AGENT_CLI_PATH", None)
