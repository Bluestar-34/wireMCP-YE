"""配置和常量定义"""

# MCP 协议版本
MCP_PROTOCOL_VERSION = "2024-11-05"

# 服务器信息
SERVER_NAME = "wiremcp-ye"
SERVER_VERSION = "1.0.0"

# 服务器默认配置
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3000

# 会话管理
SESSION_TIMEOUT = 300  # 5 minutes
HEARTBEAT_INTERVAL = 15  # seconds

# URLhaus API 配置
URLHAUS_API_URL = "https://urlhaus.abuse.ch/downloads/text/"
URLHAUS_TIMEOUT = 30.0  # seconds

# 响应限制
MAX_CHARS_IN_RESPONSE = 720000

