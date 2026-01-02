#!/usr/bin/env python3
"""
Wireshark MCP Server - 真正的 SSE MCP 实现

实现符合 MCP (Model Context Protocol) 规范的 SSE 传输层：
- GET /sse: 建立 EventSource 长连接
- POST /messages: 接收客户端 JSON-RPC 消息
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import signal
import platform
import uuid
import time
import inspect
import re
import base64
import tempfile
from typing import Dict, List, Optional, Any, Callable, Union, get_type_hints
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.requests import Request
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# ============================================================================
# 日志配置
# ============================================================================

class CustomFormatter(logging.Formatter):
    """自定义日志格式器，带颜色"""
    
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self):
        super().__init__()
        self.fmt = "%(asctime)s %(levelname)s: %(message)s"
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

# ============================================================================
# 常量定义
# ============================================================================

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "wiremcp-ye"
SERVER_VERSION = "1.0.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3000
SESSION_TIMEOUT = 300  # 5 minutes
HEARTBEAT_INTERVAL = 15  # seconds
URLHAUS_API_URL = "https://urlhaus.abuse.ch/downloads/text/"
URLHAUS_TIMEOUT = 30.0  # seconds
MAX_CHARS_IN_RESPONSE = 720000

# ============================================================================
# MCP 会话管理
# ============================================================================

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
    
    def is_expired(self, timeout: float = 300) -> bool:
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

# ============================================================================
# MCP 工具注册
# ============================================================================

@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
    
    def register(self, name: str, description: str, handler: Callable, 
                 input_schema: Optional[Dict] = None):
        """注册工具"""
        # 如果没有提供 schema，从函数签名自动生成
        if input_schema is None:
            input_schema = self._generate_schema(handler)
        
        self.tools[name] = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler
        )
        logger.debug(f"注册工具: {name}")
    
    def _generate_schema(self, func: Callable) -> Dict[str, Any]:
        """从函数签名生成 JSON Schema"""
        sig = inspect.signature(func)
        hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            param_type = hints.get(param_name, str)
            json_type = self._python_type_to_json(param_type)
            
            properties[param_name] = {"type": json_type}
            
            # 检查是否有默认值
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _python_type_to_json(self, py_type) -> str:
        """Python 类型转 JSON Schema 类型"""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            List: "array",
            dict: "object",
            Dict: "object",
        }
        
        # 处理泛型类型
        origin = getattr(py_type, '__origin__', None)
        if origin is list:
            return "array"
        if origin is dict:
            return "object"
        
        return type_map.get(py_type, "string")
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in self.tools.values()
        ]

# ============================================================================
# JSON-RPC 消息处理
# ============================================================================

class JSONRPCError(Exception):
    """JSON-RPC 错误"""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class MCPProtocolHandler:
    """MCP 协议处理器"""
    
    # MCP 协议版本
    PROTOCOL_VERSION = MCP_PROTOCOL_VERSION
    
    # 服务器信息
    SERVER_INFO = {
        "name": SERVER_NAME,
        "version": SERVER_VERSION
    }
    
    # 服务器能力
    CAPABILITIES = {
        "tools": {}
    }
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
    
    async def handle_message(self, session: MCPSession, message: Dict) -> Optional[Dict]:
        """处理 JSON-RPC 消息"""
        msg_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params", {})
        
        try:
            # 根据方法分发处理
            if method == "initialize":
                result = await self._handle_initialize(session, params)
            elif method == "notifications/initialized":
                # 这是通知，不需要响应
                return None
            elif method == "tools/list":
                result = await self._handle_tools_list(session, params)
            elif method == "tools/call":
                result = await self._handle_tools_call(session, params)
            elif method == "ping":
                result = {}
            else:
                raise JSONRPCError(-32601, f"Method not found: {method}")
            
            # 构建成功响应
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }
            return None
            
        except JSONRPCError as e:
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": e.code,
                        "message": e.message,
                        "data": e.data
                    }
                }
            return None
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
            return None
    
    async def _handle_initialize(self, session: MCPSession, params: Dict) -> Dict:
        """处理 initialize 请求"""
        session.client_info = params.get("clientInfo")
        session.initialized = True
        
        logger.info(f"会话初始化: {session.session_id}, 客户端: {session.client_info}")
        
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "capabilities": self.CAPABILITIES,
            "serverInfo": self.SERVER_INFO
        }
    
    async def _handle_tools_list(self, session: MCPSession, params: Dict) -> Dict:
        """处理 tools/list 请求"""
        tools = self.tool_registry.list_tools()
        return {"tools": tools}
    
    async def _handle_tools_call(self, session: MCPSession, params: Dict) -> Dict:
        """处理 tools/call 请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            raise JSONRPCError(-32602, f"Unknown tool: {tool_name}")
        
        try:
            # 异步或同步执行工具
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                # 在线程池中执行同步函数，避免阻塞
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: tool.handler(**arguments))
            
            # 确保结果是字符串
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False, indent=2)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
        except Exception as e:
            logger.error(f"执行工具 {tool_name} 时出错: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "error": str(e),
                            "tool": tool_name
                        }, ensure_ascii=False)
                    }
                ],
                "isError": True
            }

# ============================================================================
# SSE MCP 服务器
# ============================================================================

class SSEMCPServer:
    """真正的 SSE MCP 服务器"""
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.session_manager = SessionManager()
        self.tool_registry = ToolRegistry()
        self.protocol_handler = MCPProtocolHandler(self.tool_registry)
    
    def register_tool(self, name: str, description: str, handler: Callable,
                      input_schema: Optional[Dict] = None):
        """注册工具"""
        self.tool_registry.register(name, description, handler, input_schema)
    
    async def handle_sse(self, request: Request) -> StreamingResponse:
        """
        处理 SSE 连接请求 (GET /sse)
        
        建立 EventSource 长连接，用于服务器向客户端推送消息
        """
        # 创建新会话
        session = self.session_manager.create_session()
        
        async def event_generator():
            """SSE 事件生成器"""
            try:
                # 首先发送 endpoint 事件，告知客户端消息端点
                endpoint_url = f"/messages?session_id={session.session_id}"
                yield f"event: endpoint\ndata: {endpoint_url}\n\n"
                logger.info(f"SSE 连接建立，会话: {session.session_id}")
                
                # 心跳计数器
                heartbeat_interval = HEARTBEAT_INTERVAL
                last_heartbeat = time.time()
                
                while True:
                    try:
                        # 等待消息队列中的消息，带超时
                        try:
                            message = await asyncio.wait_for(
                                session.message_queue.get(),
                                timeout=0.5  # 更短的超时，更快响应
                            )
                            # 发送消息事件
                            data = json.dumps(message, ensure_ascii=False)
                            yield f"event: message\ndata: {data}\n\n"
                            logger.info(f"发送消息到客户端: {session.session_id}")
                            session.touch()
                        except asyncio.TimeoutError:
                            # 检查是否需要发送心跳
                            if time.time() - last_heartbeat > heartbeat_interval:
                                yield ": heartbeat\n\n"
                                last_heartbeat = time.time()
                        
                        # 检查客户端是否断开
                        if await request.is_disconnected():
                            logger.info(f"客户端断开连接，会话: {session.session_id}")
                            break
                            
                    except asyncio.CancelledError:
                        logger.info(f"SSE 连接取消，会话: {session.session_id}")
                        break
                    except Exception as e:
                        logger.error(f"SSE 循环错误: {e}")
                        break
                        
            except Exception as e:
                logger.error(f"SSE 事件生成器错误: {e}")
            finally:
                # 清理会话
                self.session_manager.remove_session(session.session_id)
                logger.info(f"SSE 连接关闭，会话已清理: {session.session_id}")
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
            }
        )
    
    async def handle_messages(self, request: Request) -> JSONResponse:
        """
        处理客户端消息 (POST /messages)
        
        接收 JSON-RPC 消息，处理后通过 SSE 推送响应
        """
        # 获取 session_id
        session_id = request.query_params.get("session_id")
        if not session_id:
            logger.warning("请求缺少 session_id")
            return JSONResponse(
                {"error": "Missing session_id"},
                status_code=400
            )
        
        # 获取会话
        session = self.session_manager.get_session(session_id)
        if not session:
            logger.warning(f"无效或过期的会话: {session_id}")
            return JSONResponse(
                {"error": "Invalid or expired session"},
                status_code=404
            )
        
        try:
            # 解析请求体
            body = await request.json()
            method = body.get("method", "unknown")
            msg_id = body.get("id", "no-id")
            logger.info(f"收到消息: method={method}, id={msg_id}, session={session_id[:8]}...")
            
            # 处理消息
            response = await self.protocol_handler.handle_message(session, body)
            
            # 如果有响应，放入消息队列
            if response:
                await session.message_queue.put(response)
                logger.info(f"响应已入队: method={method}, id={msg_id}")
            
            # 返回 202 Accepted
            return JSONResponse({"status": "accepted"}, status_code=202)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误: {e}")
            return JSONResponse(
                {"error": "Invalid JSON"},
                status_code=400
            )
        except Exception as e:
            logger.error(f"处理消息时出错: {e}", exc_info=True)
            return JSONResponse(
                {"error": str(e)},
                status_code=500
            )
    
    def create_app(self) -> Starlette:
        """创建 Starlette 应用"""
        
        async def homepage(request: Request) -> HTMLResponse:
            """状态页面"""
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Wireshark MCP 服务器</title>
                <style>
                    :root {
                        --primary-color: #1976d2;
                        --success-color: #2e7d32;
                        --background-color: #f5f5f5;
                        --card-background: white;
                        --text-color: #333;
                        --border-color: #ddd;
                    }
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                        margin: 0; padding: 0;
                        background: var(--background-color);
                        color: var(--text-color);
                        line-height: 1.6;
                    }
                    .container { 
                        max-width: 1000px; margin: 40px auto; padding: 30px;
                        background: var(--card-background);
                        border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    .header { margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid var(--border-color); }
                    .header h1 { color: var(--primary-color); margin: 0; font-size: 2.2em; }
                    .status {
                        padding: 20px; background: #e8f5e9; border-radius: 8px;
                        margin: 20px 0; color: var(--success-color);
                        display: flex; align-items: center; gap: 10px;
                    }
                    .status::before { content: "●"; color: var(--success-color); font-size: 1.5em; }
                    .endpoint-info {
                        background: #f8f9fa; padding: 20px; border-radius: 8px;
                        margin: 20px 0; border-left: 4px solid var(--primary-color);
                    }
                    .endpoint-info h3 { margin: 0 0 10px 0; color: var(--primary-color); }
                    .endpoint-info code { 
                        background: #e3f2fd; padding: 4px 8px; border-radius: 4px;
                        font-family: 'Consolas', monospace;
                    }
                    .tools-grid {
                        display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                        gap: 20px; margin: 30px 0;
                    }
                    .tool { 
                        padding: 20px; background: white;
                        border: 1px solid var(--border-color); border-radius: 8px;
                        transition: all 0.3s ease;
                    }
                    .tool:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                    .tool h3 { margin: 0 0 10px 0; color: var(--primary-color); font-size: 1.2em; }
                    .tool p { margin: 0; color: #666; font-size: 0.95em; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Wireshark MCP 服务器</h1>
                        <p>真正的 SSE MCP 实现</p>
                    </div>
                    
                    <div class="status">服务器运行正常 (SSE Mode)</div>
                    
                    <div class="endpoint-info">
                        <h3>MCP 端点配置</h3>
                        <p><strong>SSE 端点:</strong> <code>GET /sse</code></p>
                        <p><strong>消息端点:</strong> <code>POST /messages?session_id=xxx</code></p>
                        <p><strong>Cursor 配置 URL:</strong> <code>http://127.0.0.1:3000/sse</code></p>
                    </div>
                    
                    <h2>可用工具 (11 个)</h2>
                    <div class="tools-grid">
                        <div class="tool">
                            <h3>list_interfaces</h3>
                            <p>列出所有可用的网络接口</p>
                        </div>
                        <div class="tool">
                            <h3>capture_live</h3>
                            <p>实时抓包分析</p>
                        </div>
                        <div class="tool">
                            <h3>analyze_pcap</h3>
                            <p>分析 pcap 文件内容</p>
                        </div>
                        <div class="tool">
                            <h3>get_protocols</h3>
                            <p>获取支持的协议列表</p>
                        </div>
                        <div class="tool">
                            <h3>get_packet_statistics</h3>
                            <p>获取数据包统计信息</p>
                        </div>
                        <div class="tool">
                            <h3>extract_fields</h3>
                            <p>提取数据包中的特定字段</p>
                        </div>
                        <div class="tool">
                            <h3>analyze_protocols</h3>
                            <p>分析特定协议的数据包</p>
                        </div>
                        <div class="tool">
                            <h3>analyze_errors</h3>
                            <p>分析数据包中的错误</p>
                        </div>
                        <div class="tool">
                            <h3>check_threats</h3>
                            <p>捕获流量并检查威胁（URLhaus 黑名单）</p>
                        </div>
                        <div class="tool">
                            <h3>check_ip_threats</h3>
                            <p>检查特定 IP 地址的威胁</p>
                        </div>
                        <div class="tool">
                            <h3>extract_credentials</h3>
                            <p>从 PCAP 文件提取凭证（HTTP/FTP/Telnet/Kerberos）</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(html_content)
        
        # 配置中间件
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"]
            )
        ]
        
        # 配置路由
        routes = [
            Route("/", homepage),
            Route("/status", homepage),
            Route("/sse", self.handle_sse, methods=["GET"]),
            Route("/messages", self.handle_messages, methods=["POST"]),
        ]
        
        async def on_startup():
            await self.session_manager.start_cleanup_task()
            logger.info("会话清理任务已启动")
        
        async def on_shutdown():
            await self.session_manager.stop_cleanup_task()
            logger.info("会话清理任务已停止")
        
        return Starlette(
            routes=routes,
            middleware=middleware,
            on_startup=[on_startup],
            on_shutdown=[on_shutdown]
        )
    
    def run(self):
        """运行服务器"""
        app = self.create_app()
        
        logger.info(f"服务器地址: http://{self.host}:{self.port}")
        logger.info(f"状态页面: http://{self.host}:{self.port}/status")
        logger.info(f"SSE 端点: http://{self.host}:{self.port}/sse")
        logger.info(f"消息端点: http://{self.host}:{self.port}/messages")
        
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()

# ============================================================================
# Wireshark 功能实现
# ============================================================================

class WiresharkMCP:
    """Wireshark/tshark 功能封装"""
    
    def __init__(self, tshark_path: str = "tshark"):
        self.tshark_path = tshark_path
        self._verify_tshark()
        self.running = True
        
    def _verify_tshark(self):
        """验证 tshark 是否可用"""
        try:
            subprocess.run([self.tshark_path, "-v"], 
                         capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"tshark 验证失败: {e}")
            raise
        except FileNotFoundError:
            logger.error(f"找不到 tshark: {self.tshark_path}")
            raise

    def _format_json_output(self, json_str: str, max_packets: int = 5000) -> str:
        """格式化 JSON 输出"""
        try:
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "tshark_version": self._get_tshark_version(),
                "max_packets": max_packets
            }
            
            if not json_str.strip():
                return json.dumps({
                    "status": "no_data",
                    "metadata": metadata,
                    "message": "没有找到匹配的数据包",
                    "details": {
                        "possible_reasons": [
                            "过滤器可能过于严格",
                            "数据包中没有相关协议",
                            "文件可能为空"
                        ]
                    }
                }, ensure_ascii=False, indent=2)
                
            if json_str.startswith("[") or json_str.startswith("{"):
                data = json.loads(json_str)
                
                if isinstance(data, list):
                    packet_stats = {
                        "total_packets": len(data),
                        "returned_packets": min(len(data), max_packets),
                        "truncated": len(data) > max_packets
                    }
                    
                    if packet_stats["truncated"]:
                        data = data[:max_packets]
                        
                    return json.dumps({
                        "status": "success",
                        "metadata": metadata,
                        "statistics": packet_stats,
                        "data": data
                    }, ensure_ascii=False, indent=2)
                    
                return json.dumps({
                    "status": "success",
                    "metadata": metadata,
                    "data": data
                }, ensure_ascii=False, indent=2)
            
            return json.dumps({
                "status": "success",
                "metadata": metadata,
                "data": json_str.strip().split("\n")
            }, ensure_ascii=False, indent=2)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "status": "error",
                "metadata": metadata,
                "error": {
                    "type": "json_decode_error",
                    "message": str(e),
                    "raw_data": json_str[:200] + "..." if len(json_str) > 200 else json_str
                }
            }, ensure_ascii=False, indent=2)
            
    def _get_tshark_version(self) -> str:
        """获取 tshark 版本信息"""
        try:
            proc = subprocess.run([self.tshark_path, "-v"],
                                capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
            version_line = proc.stdout.split("\n")[0]
            return version_line.strip()
        except Exception:
            return "unknown"

    def _run_tshark_command(self, cmd: List[str], max_packets: int = 5000) -> str:
        """运行 tshark 命令"""
        try:
            if "-c" in cmd:
                c_index = cmd.index("-c")
                if c_index + 1 < len(cmd):
                    packet_count = max(1, int(cmd[c_index + 1]))
                    cmd[c_index + 1] = str(packet_count)
            
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
            return self._format_json_output(proc.stdout, max_packets)
        except subprocess.CalledProcessError as e:
            error_msg = f"tshark 命令执行失败: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "error": error_msg,
                "command": " ".join(cmd),
                "建议": "请检查文件路径是否正确，以及是否有读取权限"
            }, ensure_ascii=False, indent=2)

    def capture_live(self, interface: str, duration: int = 10,
                    filter: str = "", max_packets: int = 100) -> str:
        """实时抓包"""
        cmd = [
            self.tshark_path,
            "-i", interface,
            "-a", f"duration:{duration}",
            "-T", "json",
            "-c", str(max_packets)
        ]
        if filter:
            cmd.extend(["-f", filter])
        return self._run_tshark_command(cmd, max_packets)

    def list_interfaces(self) -> str:
        """列出可用的网络接口"""
        cmd = [self.tshark_path, "-D"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
            interfaces = []
            if proc.stdout:
                for line in proc.stdout.splitlines():
                    if line.strip():
                        try:
                            # 格式: "1. \Device\NPF_{...} (描述)"
                            parts = line.split(".", 1)
                            if len(parts) > 1:
                                rest = parts[1].strip()
                                if "[" in rest:
                                    name_part, desc_part = rest.split("[", 1)
                                    iface = name_part.strip()
                                    desc = desc_part.rstrip("]").strip()
                                elif "(" in rest:
                                    name_part, desc_part = rest.split("(", 1)
                                    iface = name_part.strip()
                                    desc = desc_part.rstrip(")").strip()
                                else:
                                    iface = rest.strip()
                                    desc = ""
                                interfaces.append({"name": iface, "description": desc})
                        except Exception as e:
                            logger.warning(f"解析接口行失败: {line}, 错误: {e}")
                            interfaces.append({"name": line.strip(), "description": ""})
            
            return json.dumps({
                "status": "success",
                "total": len(interfaces),
                "interfaces": interfaces
            }, ensure_ascii=False, indent=2)
        except subprocess.CalledProcessError as e:
            logger.error(f"获取接口列表失败: {e}")
            return json.dumps({
                "status": "error",
                "error": f"获取接口列表失败: {e.stderr if e.stderr else str(e)}"
            }, ensure_ascii=False, indent=2)

    def analyze_pcap(self, file_path: str, filter: str = "",
                    max_packets: int = 100) -> str:
        """分析 pcap 文件"""
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"找不到文件: {abs_path} (原始路径: {file_path})")
            
        cmd = [
            self.tshark_path,
            "-r", abs_path,
            "-T", "json",
            "-c", str(max_packets)
        ]
        if filter:
            cmd.extend(["-Y", filter])
        return self._run_tshark_command(cmd, max_packets)

    def get_protocols(self) -> str:
        """获取支持的协议列表"""
        cmd = [self.tshark_path, "-G", "protocols"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
            if proc.stdout:
                protocols = []
                for line in proc.stdout.splitlines()[:100]:  # 限制前100个
                    if line.strip():
                        parts = line.split("\t")
                        if len(parts) >= 2:
                            protocols.append({
                                "name": parts[0],
                                "description": parts[2] if len(parts) > 2 else ""
                            })
                return json.dumps({
                    "status": "success",
                    "total": len(protocols),
                    "note": "仅显示前100个协议",
                    "protocols": protocols
                }, ensure_ascii=False, indent=2)
            return json.dumps({"status": "no_data", "protocols": []}, ensure_ascii=False)
        except subprocess.CalledProcessError as e:
            return json.dumps({
                "status": "error",
                "error": f"获取协议列表失败: {e.stderr if e.stderr else str(e)}"
            }, ensure_ascii=False, indent=2)

    def get_packet_statistics(self, file_path: str, filter: str = "") -> str:
        """获取数据包统计信息"""
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        cmd = [
            self.tshark_path,
            "-r", abs_path,
            "-q",
            "-z", "io,stat,1",
            "-z", "conv,ip",
            "-z", "endpoints,ip"
        ]
        if filter:
            cmd.extend(["-Y", filter])
        return self._run_tshark_command(cmd)

    def extract_fields(self, file_path: str, fields: List[str],
                      filter: str = "", max_packets: int = 5000) -> str:
        """提取特定字段信息"""
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return json.dumps({
                "status": "error",
                "metadata": {"timestamp": datetime.now().isoformat(), "file_path": abs_path, "original_path": file_path},
                "error": {
                    "type": "file_not_found",
                    "message": f"找不到文件: {abs_path}",
                    "details": {"suggestions": ["检查文件路径是否正确", "确认文件是否存在", "验证文件访问权限"]}
                }
            }, ensure_ascii=False, indent=2)
            
        cmd = [self.tshark_path, "-r", abs_path, "-T", "fields"]
        for field in fields:
            cmd.extend(["-e", field])
        if filter:
            cmd.extend(["-Y", filter])
        if max_packets > 0:
            cmd.extend(["-c", str(max_packets)])
        
        result = self._run_tshark_command(cmd, max_packets)
        
        if isinstance(result, str) and not result.startswith("{"):
            lines = [line.strip() for line in result.splitlines() if line.strip()]
            if not lines:
                return json.dumps({
                    "status": "no_data",
                    "metadata": {"timestamp": datetime.now().isoformat(), "file_path": file_path, "fields": fields, "filter": filter},
                    "message": "没有找到匹配的数据包",
                    "details": {"fields_requested": fields, "filter_applied": filter or "无"}
                }, ensure_ascii=False, indent=2)
                
            counter = Counter(lines)
            total = len(lines)
            top10 = counter.most_common(10)
            
            stats = {
                "status": "success",
                "metadata": {"timestamp": datetime.now().isoformat(), "file_path": file_path, "fields": fields, "filter": filter},
                "statistics": {
                    "total_values": total,
                    "unique_values": len(counter),
                    "top_values": [
                        {"value": k, "count": v, "percentage": round(v/total*100, 2), "frequency": f"{v}/{total}"}
                        for k, v in top10
                    ]
                },
                "summary": {"most_common": top10[0][0] if top10 else None, "most_common_count": top10[0][1] if top10 else 0}
            }
            return json.dumps(stats, ensure_ascii=False, indent=2)
        return result

    def analyze_protocols(self, file_path: str, protocol: str = "",
                        max_packets: int = 100) -> str:
        """分析特定协议的数据包"""
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return json.dumps({
                "error": f"找不到文件: {abs_path} (原始路径: {file_path})",
                "建议": "请检查文件路径是否正确"
            }, ensure_ascii=False, indent=2)
            
        cmd = [self.tshark_path, "-r", abs_path, "-T", "json", "-c", str(max_packets)]
        if protocol:
            cmd.extend(["-Y", protocol.lower()])
            
        result = self._run_tshark_command(cmd, max_packets)
        
        try:
            data = json.loads(result)
            if isinstance(data, list):
                stats = {"协议": protocol if protocol else "all", "总数据包数": len(data), "数据包详情": data}
                return json.dumps(stats, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
        return result

    def analyze_errors(self, file_path: str, error_type: str = "all",
                      max_packets: int = 5000) -> str:
        """分析数据包中的错误"""
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return json.dumps({
                "error": f"找不到文件: {abs_path} (原始路径: {file_path})",
                "建议": "请检查文件路径是否正确"
            }, ensure_ascii=False, indent=2)
        
        filters = {
            "all": "(_ws.malformed) or (tcp.analysis.flags) or (tcp.analysis.retransmission) or (tcp.analysis.duplicate_ack) or (tcp.analysis.lost_segment)",
            "malformed": "_ws.malformed",
            "tcp": "tcp.analysis.flags",
            "retransmission": "tcp.analysis.retransmission",
            "duplicate_ack": "tcp.analysis.duplicate_ack",
            "lost_segment": "tcp.analysis.lost_segment"
        }
        
        filter_expr = filters.get(error_type, filters["all"])
        cmd = [self.tshark_path, "-r", abs_path, "-Y", filter_expr, "-T", "json", "-c", str(max_packets)]
        
        result = self._run_tshark_command(cmd, max_packets)
        
        try:
            data = json.loads(result)
            if isinstance(data, list):
                stats = {"总错误包数": len(data), "错误类型": error_type, "过滤器表达式": filter_expr, "数据包详情": data}
                return json.dumps(stats, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
        return result

    async def _fetch_urlhaus_blacklist(self) -> List[str]:
        """获取 URLhaus 黑名单 IP 列表"""
        try:
            async with httpx.AsyncClient(timeout=URLHAUS_TIMEOUT) as client:
                response = await client.get(URLHAUS_API_URL)
                response.raise_for_status()
                
                # 从文本中提取 IP 地址
                ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
                ips = re.findall(ip_pattern, response.text)
                # 去重
                unique_ips = list(set(ips))
                logger.info(f"URLhaus 黑名单加载成功: {len(unique_ips)} 个 IP")
                return unique_ips
        except Exception as e:
            logger.error(f"获取 URLhaus 黑名单失败: {e}")
            return []

    async def check_threats(self, interface: str, duration: int = 5) -> str:
        """捕获流量并检查威胁（URLhaus 黑名单）"""
        temp_pcap = None
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as f:
                temp_pcap = f.name
            
            # 捕获流量
            logger.info(f"在接口 {interface} 上捕获 {duration} 秒流量")
            cmd = [
                self.tshark_path,
                "-i", interface,
                "-w", temp_pcap,
                "-a", f"duration:{duration}"
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            
            # 提取 IP 地址
            cmd = [
                self.tshark_path,
                "-r", temp_pcap,
                "-T", "fields",
                "-e", "ip.src",
                "-e", "ip.dst"
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
            
            # 解析 IP 地址
            ips = set()
            for line in proc.stdout.split('\n'):
                parts = line.split('\t')
                for ip in parts:
                    ip = ip.strip()
                    if ip and ip != 'unknown' and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                        ips.add(ip)
            
            captured_ips = list(ips)
            logger.info(f"捕获到 {len(captured_ips)} 个唯一 IP")
            
            # 获取 URLhaus 黑名单并检查
            urlhaus_ips = await self._fetch_urlhaus_blacklist()
            threats = [ip for ip in captured_ips if ip in urlhaus_ips]
            
            result = {
                "status": "success",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "interface": interface,
                    "duration": duration
                },
                "captured_ips": captured_ips,
                "total_captured": len(captured_ips),
                "threats_found": threats,
                "threat_count": len(threats),
                "urlhaus_total": len(urlhaus_ips)
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"威胁检测失败: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e)
            }, ensure_ascii=False, indent=2)
        finally:
            # 清理临时文件
            if temp_pcap and os.path.exists(temp_pcap):
                try:
                    os.unlink(temp_pcap)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")

    async def check_ip_threats(self, ip: str) -> str:
        """检查特定 IP 地址的威胁（URLhaus 黑名单）"""
        # 验证 IP 格式
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            return json.dumps({
                "status": "error",
                "error": f"无效的 IP 地址格式: {ip}"
            }, ensure_ascii=False, indent=2)
        
        try:
            # 获取 URLhaus 黑名单
            urlhaus_ips = await self._fetch_urlhaus_blacklist()
            is_threat = ip in urlhaus_ips
            
            result = {
                "status": "success",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "ip": ip
                },
                "is_threat": is_threat,
                "threat_source": "URLhaus",
                "message": "在 URLhaus 黑名单中检测到威胁" if is_threat else "未在 URLhaus 黑名单中发现威胁"
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"IP 威胁检查失败: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e)
            }, ensure_ascii=False, indent=2)

    def extract_credentials(self, file_path: str) -> str:
        """从 PCAP 文件提取凭证（HTTP Basic Auth, FTP, Telnet, Kerberos）"""
        # 转换为绝对路径
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return json.dumps({
                "status": "error",
                "error": f"找不到文件: {abs_path} (原始路径: {file_path})"
            }, ensure_ascii=False, indent=2)
        
        credentials = {
            "plaintext": [],
            "encrypted": []
        }
        
        try:
            # 提取明文凭证字段
            cmd = [
                self.tshark_path,
                "-r", abs_path,
                "-T", "fields",
                "-e", "http.authbasic",
                "-e", "ftp.request.command",
                "-e", "ftp.request.arg",
                "-e", "telnet.data",
                "-e", "frame.number"
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
            
            # 解析明文凭证
            for line in proc.stdout.split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split('\t')
                if len(parts) < 5:
                    continue
                
                auth_basic = parts[0].strip() if len(parts) > 0 else ""
                ftp_cmd = parts[1].strip() if len(parts) > 1 else ""
                ftp_arg = parts[2].strip() if len(parts) > 2 else ""
                telnet_data = parts[3].strip() if len(parts) > 3 else ""
                frame_num = parts[4].strip() if len(parts) > 4 else ""
                
                # 处理 HTTP Basic Auth
                if auth_basic:
                    try:
                        decoded = base64.b64decode(auth_basic).decode('utf-8', errors='ignore')
                        if ':' in decoded:
                            username, password = decoded.split(':', 1)
                            credentials["plaintext"].append({
                                "type": "HTTP Basic Auth",
                                "username": username,
                                "password": password,
                                "frame": frame_num
                            })
                    except Exception as e:
                        logger.debug(f"解码 HTTP Basic Auth 失败: {e}")
                
                # 处理 FTP
                if ftp_cmd == "USER":
                    credentials["plaintext"].append({
                        "type": "FTP",
                        "username": ftp_arg,
                        "password": "",
                        "frame": frame_num
                    })
                elif ftp_cmd == "PASS":
                    # 找到最近的 FTP USER 记录并添加密码
                    for cred in reversed(credentials["plaintext"]):
                        if cred["type"] == "FTP" and not cred.get("password"):
                            cred["password"] = ftp_arg
                            break
            
            # 提取 Kerberos 凭证
            cmd = [
                self.tshark_path,
                "-r", abs_path,
                "-T", "fields",
                "-e", "kerberos.CNameString",
                "-e", "kerberos.realm",
                "-e", "kerberos.cipher",
                "-e", "kerberos.type",
                "-e", "kerberos.msg_type",
                "-e", "frame.number"
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
                for line in proc.stdout.split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split('\t')
                    if len(parts) < 6:
                        continue
                    
                    cname = parts[0].strip() if len(parts) > 0 else ""
                    realm = parts[1].strip() if len(parts) > 1 else ""
                    cipher = parts[2].strip() if len(parts) > 2 else ""
                    msg_type = parts[4].strip() if len(parts) > 4 else ""
                    frame_num = parts[5].strip() if len(parts) > 5 else ""
                    
                    if cipher and msg_type:
                        hash_format = ""
                        if msg_type in ["10", "30"]:  # AS-REQ or TGS-REQ
                            hash_format = f"$krb5pa$23${cname}${realm}${cipher}"
                            cracking_mode = "hashcat -m 7500"
                        elif msg_type == "11":  # AS-REP
                            hash_format = f"$krb5asrep$23${cname}@{realm}${cipher}"
                            cracking_mode = "hashcat -m 18200"
                        
                        if hash_format:
                            credentials["encrypted"].append({
                                "type": "Kerberos",
                                "hash": hash_format,
                                "username": cname or "unknown",
                                "realm": realm or "unknown",
                                "frame": frame_num,
                                "cracking_mode": cracking_mode
                            })
            except subprocess.CalledProcessError:
                # Kerberos 数据可能不存在，忽略错误
                pass
            
            result = {
                "status": "success",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "file_path": file_path
                },
                "plaintext_count": len(credentials["plaintext"]),
                "encrypted_count": len(credentials["encrypted"]),
                "credentials": credentials
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"提取凭证失败: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e)
            }, ensure_ascii=False, indent=2)

    def stop(self):
        """停止服务"""
        self.running = False

# ============================================================================
# 工具注册辅助函数
# ============================================================================

def register_wireshark_tools(server: SSEMCPServer, wireshark: WiresharkMCP):
    """将 Wireshark 功能注册为 MCP 工具"""
    
    # list_interfaces
    server.register_tool(
        name="list_interfaces",
        description="列出所有可用的网络接口，返回接口名称和描述信息",
        handler=wireshark.list_interfaces,
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
    
    # capture_live
    server.register_tool(
        name="capture_live",
        description="实时抓包分析。需要指定网络接口，可设置抓包时长和过滤器",
        handler=wireshark.capture_live,
        input_schema={
            "type": "object",
            "properties": {
                "interface": {"type": "string", "description": "网络接口名称"},
                "duration": {"type": "integer", "description": "抓包持续时间(秒)，默认10秒", "default": 10},
                "filter": {"type": "string", "description": "抓包过滤器表达式", "default": ""},
                "max_packets": {"type": "integer", "description": "最大数据包数量，默认100", "default": 100}
            },
            "required": ["interface"]
        }
    )
    
    # analyze_pcap
    server.register_tool(
        name="analyze_pcap",
        description="分析 pcap/pcapng 文件内容，支持过滤器",
        handler=wireshark.analyze_pcap,
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "pcap 文件路径"},
                "filter": {"type": "string", "description": "显示过滤器表达式", "default": ""},
                "max_packets": {"type": "integer", "description": "最大数据包数量，默认100", "default": 100}
            },
            "required": ["file_path"]
        }
    )
    
    # get_protocols
    server.register_tool(
        name="get_protocols",
        description="获取 tshark 支持的所有协议列表",
        handler=wireshark.get_protocols,
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
    
    # get_packet_statistics
    server.register_tool(
        name="get_packet_statistics",
        description="获取 pcap 文件的统计信息，包括 I/O 统计、IP 会话和端点统计",
        handler=wireshark.get_packet_statistics,
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "pcap 文件路径"},
                "filter": {"type": "string", "description": "显示过滤器表达式", "default": ""}
            },
            "required": ["file_path"]
        }
    )
    
    # extract_fields
    server.register_tool(
        name="extract_fields",
        description="从 pcap 文件中提取特定字段信息，返回字段值统计",
        handler=wireshark.extract_fields,
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "pcap 文件路径"},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "要提取的字段列表，如 ['ip.src', 'ip.dst']"},
                "filter": {"type": "string", "description": "显示过滤器表达式", "default": ""},
                "max_packets": {"type": "integer", "description": "最大数据包数量，默认5000", "default": 5000}
            },
            "required": ["file_path", "fields"]
        }
    )
    
    # analyze_protocols
    server.register_tool(
        name="analyze_protocols",
        description="分析特定协议的数据包，如 http、tcp、dns 等",
        handler=wireshark.analyze_protocols,
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "pcap 文件路径"},
                "protocol": {"type": "string", "description": "协议名称，如 http, tcp, dns", "default": ""},
                "max_packets": {"type": "integer", "description": "最大数据包数量，默认100", "default": 100}
            },
            "required": ["file_path"]
        }
    )
    
    # analyze_errors
    server.register_tool(
        name="analyze_errors",
        description="分析数据包中的错误，包括畸形包、TCP 重传、重复 ACK、丢失段等",
        handler=wireshark.analyze_errors,
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "pcap 文件路径"},
                "error_type": {
                    "type": "string",
                    "description": "错误类型: all/malformed/tcp/retransmission/duplicate_ack/lost_segment",
                    "default": "all",
                    "enum": ["all", "malformed", "tcp", "retransmission", "duplicate_ack", "lost_segment"]
                },
                "max_packets": {"type": "integer", "description": "最大数据包数量，默认5000", "default": 5000}
            },
            "required": ["file_path"]
        }
    )
    
    # check_threats - 捕获流量并检查威胁
    server.register_tool(
        name="check_threats",
        description="捕获实时流量并检查 IP 地址 against URLhaus 黑名单",
        handler=wireshark.check_threats,
        input_schema={
            "type": "object",
            "properties": {
                "interface": {"type": "string", "description": "网络接口名称（如 eth0, en0）"},
                "duration": {"type": "integer", "description": "抓包持续时间(秒)，默认5秒", "default": 5}
            },
            "required": ["interface"]
        }
    )
    
    # check_ip_threats - 检查特定 IP 威胁
    server.register_tool(
        name="check_ip_threats",
        description="检查特定 IP 地址 against URLhaus 黑名单",
        handler=wireshark.check_ip_threats,
        input_schema={
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "要检查的 IP 地址（如 192.168.1.1）"}
            },
            "required": ["ip"]
        }
    )
    
    # extract_credentials - 提取凭证
    server.register_tool(
        name="extract_credentials",
        description="从 PCAP 文件提取凭证，包括 HTTP Basic Auth、FTP、Telnet 和 Kerberos 哈希",
        handler=wireshark.extract_credentials,
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "pcap 文件路径"}
            },
            "required": ["file_path"]
        }
    )
    
    logger.info(f"已注册 {len(server.tool_registry.tools)} 个 Wireshark 工具")

# ============================================================================
# 主入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Wireshark MCP 服务器 (SSE)")
    parser.add_argument("--tshark-path", default="tshark", help="tshark 可执行文件路径")
    parser.add_argument("--host", default=DEFAULT_HOST, help="服务器主机地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="服务器端口")
    args = parser.parse_args()
    
    # 获取系统信息
    info = {
        "python_version": platform.python_version(),
        "os_platform": platform.platform()
    }
    logger.info(f"Python: {info['python_version']}, OS: {info['os_platform']}")
    
    try:
        # 初始化 Wireshark
        wireshark = WiresharkMCP(args.tshark_path)
        logger.info(f"tshark 版本: {wireshark._get_tshark_version()}")
        
        # 创建 SSE MCP 服务器
        server = SSEMCPServer(host=args.host, port=args.port)
        
        # 注册工具
        register_wireshark_tools(server, wireshark)
        
        # 运行服务器
        server.run()
        
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
