# 模块化重构计划

## 当前状态

### ✅ 日志功能
- 有完整的日志系统
- 自定义格式化器（带颜色）
- 45+ 个日志调用点
- 日志级别：INFO, DEBUG, WARNING, ERROR, CRITICAL

### ❌ 模块化状态
- 所有代码在单一文件 `wireshark_mcp.py` (1581行)
- 包含6个主要类
- 50+ 个函数/方法
- 代码组织不够清晰

## 模块化方案

### 目标结构

```
wireMCP-YE/
├── wireshark_mcp/
│   ├── __init__.py              # 包初始化
│   ├── main.py                  # 主入口
│   ├── config.py                # 配置和常量
│   ├── logger.py                # 日志配置
│   ├── session.py               # 会话管理
│   ├── tools.py                 # 工具注册
│   ├── protocol.py              # MCP 协议处理
│   ├── server.py                # SSE 服务器
│   └── wireshark.py             # Wireshark 功能封装
├── tests/
│   └── ...
└── wireshark_mcp.py             # 向后兼容入口（可选）
```

### 模块划分

1. **config.py** - 常量配置
   - MCP_PROTOCOL_VERSION
   - SERVER_NAME, SERVER_VERSION
   - DEFAULT_HOST, DEFAULT_PORT
   - SESSION_TIMEOUT, HEARTBEAT_INTERVAL
   - URLHAUS_API_URL, URLHAUS_TIMEOUT
   - MAX_CHARS_IN_RESPONSE

2. **logger.py** - 日志系统
   - CustomFormatter 类
   - setup_logger() 函数
   - get_logger() 函数

3. **session.py** - 会话管理
   - MCPSession 类
   - SessionManager 类

4. **tools.py** - 工具注册
   - MCPTool 类
   - ToolRegistry 类

5. **protocol.py** - 协议处理
   - JSONRPCError 类
   - MCPProtocolHandler 类

6. **server.py** - SSE 服务器
   - SSEMCPServer 类

7. **wireshark.py** - Wireshark 功能
   - WiresharkMCP 类
   - 所有工具方法

8. **main.py** - 主入口
   - main() 函数
   - 参数解析
   - 服务器启动

## 重构步骤

1. 创建包目录结构
2. 提取常量到 config.py
3. 提取日志到 logger.py
4. 拆分各个类到对应模块
5. 更新导入语句
6. 创建主入口
7. 保持向后兼容
8. 更新测试

## 优势

- ✅ 代码组织清晰
- ✅ 易于维护和扩展
- ✅ 便于单元测试
- ✅ 符合 Python 最佳实践
- ✅ 更好的代码复用性


