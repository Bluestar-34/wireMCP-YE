# WireMCP-YE 使用说明

## 📋 模块化和日志功能状态

### ✅ 日志功能

**状态**: 已完整实现且功能完善

**功能特性：**
- ✅ 完整的 Python logging 模块集成
- ✅ 自定义颜色格式化器（彩色输出）
- ✅ 5种日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
- ✅ 45+ 个日志调用点，覆盖所有关键操作
- ✅ 时间戳格式化
- ✅ 控制台输出

**日志使用位置：**
- 会话管理（创建、删除、超时清理）
- 消息处理（接收、响应、错误）
- SSE 连接（建立、关闭、心跳）
- 工具执行（调用、结果）
- Wireshark 操作（命令执行、错误处理）

**日志级别说明：**
- `INFO`: 正常操作信息（会话创建、消息处理等）
- `ERROR`: 错误信息（异常、失败操作）
- `WARNING`: 警告信息（无效请求、过期会话等）
- `DEBUG`: 调试信息（工具注册等详细操作）

### 🔄 模块化状态

**当前状态**: 部分模块化（正在进行中）

**已完成模块：**
- ✅ `wireshark_mcp/__init__.py` - 包初始化
- ✅ `wireshark_mcp/config.py` - 配置和常量
- ✅ `wireshark_mcp/logger.py` - 日志系统（增强版）
- ✅ `wireshark_mcp/session.py` - 会话管理

**待完成模块：**
- ⏳ `wireshark_mcp/tools.py` - 工具注册
- ⏳ `wireshark_mcp/protocol.py` - MCP 协议处理
- ⏳ `wireshark_mcp/server.py` - SSE 服务器
- ⏳ `wireshark_mcp/wireshark.py` - Wireshark 功能封装
- ⏳ `wireshark_mcp/main.py` - 主入口

**当前代码结构：**
- 主文件：`wireshark_mcp.py` (1581行) - 包含所有功能
- 模块包：`wireshark_mcp/` - 正在构建的模块化结构

## 📖 使用方法

### 1. 安装

```bash
# 进入项目目录
cd wireMCP-YE

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动服务器

```bash
# 使用默认配置启动
python wireshark_mcp.py

# 自定义配置启动
python wireshark_mcp.py --host 0.0.0.0 --port 3000 --tshark-path /usr/bin/tshark
```

**启动参数：**
- `--host`: 服务器主机地址（默认：127.0.0.1）
- `--port`: 服务器端口（默认：3000）
- `--tshark-path`: tshark 可执行文件路径（默认：tshark）

### 3. 查看日志

服务器启动后，会在控制台输出彩色日志：

```
14:30:15 INFO: Python: 3.10.0, OS: Windows-10
14:30:15 INFO: tshark 版本: TShark (Wireshark) 4.0.0
14:30:15 INFO: 服务器地址: http://127.0.0.1:3000
14:30:15 INFO: SSE 端点: http://127.0.0.1:3000/sse
14:30:15 INFO: 消息端点: http://127.0.0.1:3000/messages
14:30:15 INFO: 已注册 11 个 Wireshark 工具
14:30:15 INFO: 会话清理任务已启动
```

**日志颜色说明：**
- 🔵 蓝色 - INFO 级别
- 🟡 黄色 - WARNING 级别
- 🔴 红色 - ERROR 级别
- ⚫ 灰色 - DEBUG 级别

### 4. 配置 Cursor IDE

在项目根目录或 `.cursor` 目录创建 `mcp.json`：

```json
{
  "mcpServers": {
    "wireshark": {
      "url": "http://127.0.0.1:3000/sse"
    }
  }
}
```

### 5. 访问状态页面

打开浏览器访问：
- 状态页面：http://127.0.0.1:3000/status
- 或主页：http://127.0.0.1:3000/

## 🛠️ 日志功能使用

### 在当前代码中使用日志

**方式1：使用全局 logger（当前代码）**
```python
from wireshark_mcp import logger

logger.info("这是一条信息")
logger.error("这是一条错误")
logger.warning("这是一条警告")
```

**方式2：使用模块化 logger（推荐）**
```python
from wireshark_mcp.logger import get_logger

logger = get_logger(__name__)
logger.info("模块化日志")
```

### 日志配置

**使用默认配置（带颜色）：**
```python
from wireshark_mcp.logger import setup_logger

logger = setup_logger("my_module")
```

**禁用颜色（用于文件输出）：**
```python
logger = setup_logger("my_module", use_color=False)
```

**自定义日志级别：**
```python
import logging
logger = setup_logger("my_module", level=logging.DEBUG)
```

## 📊 模块化使用

### 当前状态

**使用单文件版本（当前）：**
```python
# 直接运行
python wireshark_mcp.py
```

**使用模块化版本（开发中）：**
```python
# 导入模块
from wireshark_mcp import main, SSEMCPServer, WiresharkMCP

# 或使用包
python -m wireshark_mcp
```

### 模块导入示例

**配置模块：**
```python
from wireshark_mcp.config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    SESSION_TIMEOUT,
    URLHAUS_API_URL
)
```

**日志模块：**
```python
from wireshark_mcp.logger import get_logger, setup_logger

logger = get_logger(__name__)
```

**会话管理：**
```python
from wireshark_mcp.session import MCPSession, SessionManager

manager = SessionManager()
session = manager.create_session()
```

## 🔍 常见问题

### Q: 日志没有颜色？
A: 确保终端支持 ANSI 颜色代码。在 Windows PowerShell 中可能需要额外配置。

### Q: 如何查看 DEBUG 级别日志？
A: 修改日志级别：
```python
logger.setLevel(logging.DEBUG)
```

### Q: 模块化代码何时完成？
A: 模块化重构正在进行中，当前已完成 25%（4个模块）。完整版本将在后续版本中发布。

### Q: 当前代码可以正常使用吗？
A: 是的，当前的单文件版本完全可用，所有功能正常。模块化是改进，不影响功能。

## 📚 相关文档

- `MODULAR_STATUS.md` - 模块化状态详细报告
- `MODULARIZATION_PLAN.md` - 模块化重构计划
- `README.md` - 项目主文档
- `PROJECT_STRUCTURE.md` - 项目结构说明

## 📝 总结

**日志功能：** ✅ 完整实现，功能完善，可立即使用

**模块化：** 🔄 部分完成（25%），基础模块已就绪，完整模块化进行中

**建议：**
- 日志功能已完整，可直接使用
- 当前单文件结构完全可用
- 模块化改进将提高代码可维护性
- 可根据需要选择单文件或模块化版本

