"""会话管理模块"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from .config import SESSION_TIMEOUT
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class MCPSession:
    """MCP 会话，管理单个客户端连接的生命周期"""
    session_id: str
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    initialized: bool = False
    client_info: Optional[Dict] = None
    
    def touch(self):
        """更新最后活跃时间"""
        self.last_active = time.time()
    
    def is_expired(self, timeout: float = SESSION_TIMEOUT) -> bool:
        """检查会话是否超时（默认5分钟）"""
        return time.time() - self.last_active > timeout


class SessionManager:
    """会话管理器，处理所有活跃会话"""
    
    def __init__(self, session_timeout: float = SESSION_TIMEOUT):
        self.sessions: Dict[str, MCPSession] = {}
        self.session_timeout = session_timeout
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def create_session(self) -> MCPSession:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        session = MCPSession(session_id=session_id)
        self.sessions[session_id] = session
        logger.info(f"创建新会话: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[MCPSession]:
        """获取会话"""
        session = self.sessions.get(session_id)
        if session:
            session.touch()
        return session
    
    def remove_session(self, session_id: str):
        """移除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"移除会话: {session_id}")
    
    async def start_cleanup_task(self):
        """启动定期清理任务"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup_task(self):
        """停止清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """定期清理过期会话"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                expired = [
                    sid for sid, session in self.sessions.items()
                    if session.is_expired(self.session_timeout)
                ]
                for sid in expired:
                    self.remove_session(sid)
                    logger.info(f"清理过期会话: {sid}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理会话时出错: {e}")

