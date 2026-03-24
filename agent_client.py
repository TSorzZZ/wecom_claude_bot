"""
Claude Agent SDK 封装：集成 Claude Code channel 能力

通过 claude-agent-sdk 启动 Claude Code CLI 子进程，支持：
- Read / Write / Edit 文件操作
- Bash 命令执行
- Glob / Grep 代码搜索
- WebSearch / WebFetch 网页搜索

多轮对话通过 session_id 实现，/clear 命令丢弃 session 重新开始。
"""
import logging
import os
from typing import AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    CLINotFoundError,
    ResultMessage,
    TextBlock,
    query,
)

from config import (
    AGENT_ALLOWED_TOOLS,
    AGENT_CLI_PATH,
    AGENT_CWD,
    ANTHROPIC_API_KEY,
    ANTHROPIC_BASE_URL,
    CLAUDE_MODEL,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

# user_id → session_id（None 表示下次调用创建新 session）
_sessions: dict[str, str | None] = {}

_TOOL_LABELS: dict[str, str] = {
    "Bash": "执行命令",
    "Read": "读取文件",
    "Write": "写入文件",
    "Edit": "编辑文件",
    "Glob": "搜索文件",
    "Grep": "搜索内容",
    "WebSearch": "网络搜索",
    "WebFetch": "获取网页",
    "Agent": "调用子 Agent",
}


def clear_session(user_id: str) -> None:
    """丢弃 session ID，下次 agent_stream 将开启全新对话。"""
    _sessions.pop(user_id, None)


async def agent_stream(
    user_id: str,
    text: str,
) -> AsyncIterator[tuple[str, bool]]:
    """
    异步生成器，每次 yield (accumulated_text, is_tool_event)。

    accumulated_text: 截至当前的全部可见内容（replace 模式，适配 WeCom 流式协议）
    is_tool_event: True 表示这帧是工具使用状态提示（非最终文本）

    生成器结束后 session_id 已保存，下次调用自动续接对话。
    """
    session_id = _sessions.get(user_id)
    accumulated = ""

    # 构建传给 CLI 子进程的环境变量
    # 优先从运行时环境动态读取（claude-internal 注入的临时 token），
    # 回退到 .env 中的静态配置
    runtime_token = (
        os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or os.environ.get("ANTHROPIC_API_KEY")
        or ANTHROPIC_API_KEY
    )
    runtime_base_url = os.environ.get("ANTHROPIC_BASE_URL") or ANTHROPIC_BASE_URL
    runtime_custom_headers = os.environ.get("ANTHROPIC_CUSTOM_HEADERS", "")

    agent_env: dict[str, str] = {"ANTHROPIC_API_KEY": runtime_token}
    if runtime_base_url:
        agent_env["ANTHROPIC_BASE_URL"] = runtime_base_url
    if runtime_custom_headers:
        agent_env["ANTHROPIC_CUSTOM_HEADERS"] = runtime_custom_headers

    options = ClaudeAgentOptions(
        cwd=AGENT_CWD,
        allowed_tools=AGENT_ALLOWED_TOOLS,
        permission_mode="bypassPermissions",
        model=CLAUDE_MODEL,
        system_prompt=SYSTEM_PROMPT,
        resume=session_id,  # None = 新 session；str = 续接
        env=agent_env,
        cli_path=AGENT_CLI_PATH,  # 使用 claude-internal 替代 claude
    )

    try:
        async for message in query(prompt=text, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text:
                        accumulated += block.text
                        yield (accumulated, False)
                    elif hasattr(block, "name"):  # ToolUseBlock
                        label = _TOOL_LABELS.get(block.name, block.name)
                        # 工具使用状态帧：在累积文本后追加提示，不计入最终内容
                        yield (accumulated + f"\n\n🔧 [正在使用工具: {label}...]", True)

            elif isinstance(message, ResultMessage):
                # 保存 session_id 供下次续接
                _sessions[user_id] = message.session_id
                # 若 agent 全程只用工具未输出文本，用 result 摘要兜底
                if not accumulated and message.result:
                    accumulated = message.result
                return

    except CLINotFoundError:
        _sessions.pop(user_id, None)
        logger.error("未找到 Claude CLI，user=%s", user_id)
        raise
    except Exception:
        _sessions.pop(user_id, None)
        logger.exception("Agent 调用异常 user=%s", user_id)
        raise
