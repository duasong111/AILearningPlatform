"""
Redis 状态键常量 —— 维护 LLM 任务执行期间的瞬时态。

依赖 settings.CACHES 已配的 django_redis 后端，调用方用 `from django.core.cache import cache`。
"""
TTL_SEC = 3600           # 1h，所有键的统一过期时间
STALE_SEC = 300          # 5min，msg 超过这个时间还在 "generating" 视为 stale


def msg_state(message_id: int) -> str:
    """值: 'generating' | 'complete' | 'error:<msg>'"""
    return f"msg:{message_id}:state"


def msg_content(message_id: int) -> str:
    """值: LLM 已 chunk 累计的字符串（断线可回放）"""
    return f"msg:{message_id}:content"


def msg_meta(message_id: int) -> str:
    """值: JSON-serializable dict，保存 complete 阶段的结构化结果。"""
    return f"msg:{message_id}:meta"


def msg_started_at(message_id: int) -> str:
    """值: float 时间戳（判 stale 用）"""
    return f"msg:{message_id}:started_at"


def conv_current_ai_msg(conversation_id: int) -> str:
    """值: 当前在生成的 AI 消息 id（前端 GET conversation 一次拿到）"""
    return f"conv:{conversation_id}:current_ai_msg"


def conv_ai_state(conversation_id: int) -> str:
    """值: 'idle' | 'generating'"""
    return f"conv:{conversation_id}:ai_state"


def conv_channel_group(conversation_id: int) -> str:
    """Conversation 级别的 channel layer group 名。"""
    return f"conv.{conversation_id}"


def msg_channel_group(message_id: int) -> str:
    """Channel layer group 名。WS consumer 加入这个 group 收 LLM 流事件。"""
    return f"msg.{message_id}"
