"""
企业微信智能机器人（长连接模式）× Claude

特性：
- 基于官方 wecom-aibot-python-sdk WebSocket 长连接，无需公网 URL
- 流式回复：Claude 边生成边推送，用户实时看到文字出现（打字机效果）
- 多轮对话：每个用户独立保存对话历史
- 支持 /clear /help 指令
- 用户进入会话时自动发送欢迎语
"""

import asyncio
import logging

from aibot import WSClient, WSClientOptions
from aibot.types import EventType

import agent_client
from config import (
    CLAUDE_MODEL,
    WECOM_BOT_ID,
    WECOM_SECRET,
)
from utils import generate_stream_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

_CMD_CLEAR = "/clear"
_CMD_HELP  = "/help"
_HELP_TEXT = (
    "🤖 **WeCom Claude Bot**\n\n"
    "直接发消息即可与 Claude 对话，支持多轮连续对话。\n\n"
    "**可用指令：**\n"
    "`/clear` — 清除对话记录，重新开始\n"
    "`/help`  — 显示此帮助"
)


async def main() -> None:
    client = WSClient(
        WSClientOptions(
            bot_id=WECOM_BOT_ID,
            secret=WECOM_SECRET,
            max_reconnect_attempts=-1,   # 无限重连
            heartbeat_interval=30_000,
        )
    )

    # ── 连接事件 ──────────────────────────────────────────────────────────

    @client.on("connected")
    def on_connected() -> None:
        logger.info("WebSocket 已连接")

    @client.on("authenticated")
    def on_authenticated() -> None:
        logger.info("认证成功，机器人在线 ✅  model=%s", CLAUDE_MODEL)

    @client.on("disconnected")
    def on_disconnected(reason: str) -> None:
        logger.warning("连接断开：%s", reason)

    @client.on("reconnecting")
    def on_reconnecting(attempt: int) -> None:
        logger.info("正在重连（第 %d 次）…", attempt)

    @client.on("error")
    def on_error(err: Exception) -> None:
        logger.error("连接错误：%s", err)

    # ── 进入会话事件（发欢迎语）────────────────────────────────────────────

    @client.on(f"event.{EventType.EnterChat}")
    async def on_enter_chat(frame: dict) -> None:
        body = frame.get("body", {})
        user_id = body.get("from", {}).get("user_id", "unknown")
        logger.info("用户进入会话：%s", user_id)
        await client.reply_welcome(
            frame,
            {
                "msgtype": "text",
                "text": {
                    "content": (
                        "你好！我是基于 Claude 的 AI 助手 👋\n"
                        "有什么可以帮你的？发送 /help 查看帮助。"
                    )
                },
            },
        )

    # ── 文本消息（核心处理逻辑）────────────────────────────────────────────

    @client.on("message.text")
    async def on_text_message(frame: dict) -> None:
        body = frame.get("body", {})
        user_id = body.get("from", {}).get("user_id", "unknown")
        text = body.get("text", {}).get("content", "").strip()

        logger.info("收到消息 user=%s：%s", user_id, text[:80])

        # ── 内置指令 ──────────────────────────────────────────────────────
        if text.lower() == _CMD_CLEAR:
            agent_client.clear_session(user_id)
            await client.reply(
                frame,
                {"msgtype": "text", "text": {"content": "✅ 对话记录已清除，开始新对话吧！"}},
            )
            return

        if text.lower() == _CMD_HELP:
            await client.reply(
                frame,
                {"msgtype": "text", "text": {"content": _HELP_TEXT}},
            )
            return

        # ── 流式调用 Claude Code Agent ──────────────────────────────────────
        stream_id = generate_stream_id()
        full_reply = ""

        # 立即反馈，避免用户等待无响应
        await client.reply_stream(
            frame,
            stream_id=stream_id,
            content="⏳ 正在思考...",
            finish=False,
        )

        try:
            async for content, _ in agent_client.agent_stream(user_id, text):
                full_reply = content  # 已是累积内容，符合 WeCom replace 模式
                await client.reply_stream(
                    frame,
                    stream_id=stream_id,
                    content=full_reply,
                    finish=False,
                )

            # 发送结束帧
            await client.reply_stream(
                frame,
                stream_id=stream_id,
                content=full_reply or "（无回复）",
                finish=True,
            )
            logger.info("回复完成 user=%s，共 %d 字符", user_id, len(full_reply))

        except Exception as exc:
            logger.exception("Agent 调用失败 user=%s", user_id)
            err_msg = f"❌ AI 调用出错：{exc}\n可发送 /clear 重置对话后重试。"
            await client.reply_stream(
                frame,
                stream_id=stream_id,
                content=err_msg,
                finish=True,
            )

    # ── 启动 ──────────────────────────────────────────────────────────────
    logger.info("正在连接企业微信智能机器人长连接服务…")
    await client.connect()

    # 保持运行直到 Ctrl+C
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        client.disconnect()
        logger.info("已退出")


if __name__ == "__main__":
    asyncio.run(main())
