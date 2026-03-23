"""工具函数"""
import uuid


def generate_stream_id() -> str:
    """生成流式消息唯一 ID（UUID4 去横线）"""
    return uuid.uuid4().hex
