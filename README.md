# WireMCP-YE - 统一的 Wireshark MCP 服务器

一个融合了 Python SSE 实现和 Node.js 功能的统一 Wireshark MCP 服务器。

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-black.svg)](https://github.com/astral-sh/ruff)

## ✨ 特性

- **完整的 SSE 实现**：基于 Python 版本的优秀 SSE 架构
- **11 个强大工具**：融合两个版本的所有功能
- **威胁检测**：集成 URLhaus 黑名单检查
- **凭证提取**：支持 HTTP Basic Auth、FTP、Telnet、Kerberos
- **零外部 MCP 依赖**：完全自包含实现

## 🛠️ 工具列表

### 基础工具（8个）
1. `list_interfaces` - 列出所有可用的网络接口
2. `capture_live` - 实时抓包分析
3. `analyze_pcap` - 分析 pcap/pcapng 文件
4. `get_protocols` - 获取 tshark 支持的协议列表
5. `get_packet_statistics` - 获取数据包统计信息
6. `extract_fields` - 提取特定字段并统计
7. `analyze_protocols` - 分析特定协议的数据包
8. `analyze_errors` - 分析网络错误

### 安全工具（3个 - 新增）
9. `check_threats` - 捕获流量并检查 IP against URLhaus 黑名单
10. `check_ip_threats` - 检查特定 IP 地址的威胁
11. `extract_credentials` - 从 PCAP 文件提取凭证（HTTP/FTP/Telnet/Kerberos）

## 📦 安装

### 前置要求
- Python 3.8+
- Wireshark (需要 `tshark` 命令行工具)

### 安装步骤

```bash
# 进入目录
cd wireMCP-YE

# 安装依赖
pip install -r requirements.txt
```

## 🚀 使用方法

### 启动服务器

```bash
python wireshark_mcp.py
```

可选参数：
```bash
python wireshark_mcp.py --host 127.0.0.1 --port 3000 --tshark-path /path/to/tshark
```

### 配置 Cursor IDE

在项目根目录创建 `mcp.json`（或 `.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "wireshark": {
      "url": "http://127.0.0.1:3000/sse"
    }
  }
}
```

## 🔧 新功能详解

### check_threats

捕获实时流量并检查 IP 地址是否在 URLhaus 黑名单中。

```json
{
  "interface": "eth0",
  "duration": 5
}
```

### check_ip_threats

检查特定 IP 地址的威胁状态。

```json
{
  "ip": "192.168.1.1"
}
```

### extract_credentials

从 PCAP 文件提取各种类型的凭证：

- **HTTP Basic Auth**：Base64 解码的用户名和密码
- **FTP**：USER 和 PASS 命令中的凭证
- **Telnet**：登录凭证
- **Kerberos**：哈希格式的 Kerberos 凭证（支持 hashcat）

```json
{
  "file_path": "./capture.pcap"
}
```

## 📊 工具对比

| 功能 | Python 原版 | Node.js 原版 | WireMCP-YE |
|------|------------|-------------|------------|
| 基础抓包 | ✅ | ✅ | ✅ |
| 协议分析 | ✅ | ✅ | ✅ |
| 威胁检测 | ❌ | ✅ | ✅ |
| 凭证提取 | ❌ | ✅ | ✅ |
| SSE 传输 | ✅ | ❌ | ✅ |
| Web 界面 | ✅ | ❌ | ✅ |
| 工具总数 | 8 | 7 | **11** |

## 🏗️ 架构

```
┌─────────────────┐     GET /sse      ┌──────────────────┐
│   Cursor IDE    │ ◄───────────────► │  SSE MCP Server  │
│  (MCP Client)   │                   │                  │
│                 │  POST /messages   │  - SessionMgr    │
│                 │ ────────────────► │  - ToolRegistry  │
│                 │                   │  - WiresharkMCP  │
└─────────────────┘                   └──────────────────┘
                                              │
                                              ▼
                                      ┌──────────────┐
                                      │   tshark     │
                                      │ (Wireshark)  │
                                      └──────────────┘
                                              │
                                              ▼
                                      ┌──────────────┐
                                      │  URLhaus API │
                                      │  (威胁检测)   │
                                      └──────────────┘
```

## 🔍 端点说明

| 端点 | 方法 | 描述 |
|-----|------|------|
| `/` | GET | 状态页面 |
| `/status` | GET | 状态页面 |
| `/sse` | GET | SSE 长连接端点 |
| `/messages` | POST | JSON-RPC 消息接收端点 |

## 📝 许可证

MIT License

## 🙏 致谢

- Python 版本原作者（落雨）
- Node.js 版本原作者（0xKoda）
- Wireshark/tshark 团队
- URLhaus 提供的威胁情报数据

