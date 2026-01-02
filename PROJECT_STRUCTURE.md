# 项目结构说明

## 目录结构

```
wireMCP-YE/
├── wireshark_mcp.py          # 主程序入口
├── requirements.txt           # 生产环境依赖
├── pyproject.toml            # 项目配置（PEP 518 标准）
├── README.md                 # 项目文档和使用说明
├── CONTRIBUTING.md           # 贡献指南
├── CHANGELOG.md              # 版本更新日志
├── CODE_OF_CONDUCT.md        # 行为准则
├── LICENSE                   # MIT 许可证
├── UNIFICATION_SUMMARY.md    # 统一总结文档
├── .gitignore                # Git 忽略文件
├── .editorconfig             # 编辑器配置
├── .pre-commit-config.yaml   # Pre-commit 钩子配置
├── mcp.json                  # MCP 配置示例
└── tests/                    # 测试目录
    ├── __init__.py
    └── conftest.py           # Pytest 配置和 fixtures
```

## 文件说明

### 核心文件

- **wireshark_mcp.py**: 主程序文件，包含所有核心功能
  - MCP 会话管理
  - 工具注册表
  - JSON-RPC 协议处理
  - SSE 服务器实现
  - Wireshark 功能封装

### 配置文件

- **pyproject.toml**: 现代 Python 项目配置文件
  - 项目元数据
  - 依赖管理
  - 代码质量工具配置（Ruff, MyPy, Pytest）

- **requirements.txt**: 生产环境依赖列表

- **.gitignore**: Git 版本控制忽略规则

- **.editorconfig**: 编辑器统一配置（缩进、编码等）

- **.pre-commit-config.yaml**: 提交前代码检查配置

### 文档文件

- **README.md**: 主要文档，包含安装和使用说明

- **CONTRIBUTING.md**: 贡献者指南，开发流程和代码规范

- **CHANGELOG.md**: 版本更新记录

- **CODE_OF_CONDUCT.md**: 社区行为准则

- **UNIFICATION_SUMMARY.md**: 统一方案总结文档

### 测试文件

- **tests/**: 测试目录
  - `__init__.py`: 包初始化文件
  - `conftest.py`: Pytest 配置和共享 fixtures

## 代码组织

### 模块结构

```python
# 常量定义
MCP_PROTOCOL_VERSION = "..."
SERVER_NAME = "..."
# ...

# 日志配置
class CustomFormatter(...)
logger = ...

# 会话管理
class MCPSession(...)
class SessionManager(...)

# 工具注册
class MCPTool(...)
class ToolRegistry(...)

# 协议处理
class JSONRPCError(...)
class MCPProtocolHandler(...)

# SSE 服务器
class SSEMCPServer(...)

# Wireshark 功能
class WiresharkMCP(...)

# 工具注册函数
def register_wireshark_tools(...)

# 主入口
def main()
```

### 设计原则

1. **单一职责**: 每个类负责一个明确的功能
2. **依赖注入**: 通过构造函数注入依赖
3. **异步优先**: 使用 async/await 处理 I/O 操作
4. **错误处理**: 完善的异常处理和日志记录
5. **类型注解**: 使用类型提示提高代码可读性

## 开发流程

1. **本地开发**: 在虚拟环境中开发
2. **代码检查**: 使用 Ruff 和 MyPy 检查代码
3. **运行测试**: 使用 Pytest 运行测试套件
4. **提交代码**: Pre-commit 钩子自动检查
5. **创建 PR**: 遵循 CONTRIBUTING.md 指南


