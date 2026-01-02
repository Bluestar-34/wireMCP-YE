# WireMCP-YE - Wireshark MCP 服务器

一个强大的 Wireshark MCP (Model Context Protocol) 服务器，为 AI 提供流量分析的辅助工具。

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-purple.svg)](https://modelcontextprotocol.io)

## 🎯 核心理念

**MCP 是辅助工具，不是完整解决方案**

- MCP 工具提供**信息和线索**
- AI 进行**分析和决策**
- 真正的能力来自 AI 的**思考和创造**

```
MCP 工具 → 获取信息 → AI 分析判断 → AI 自主决策 → 执行操作 → 解决问题
```

## ✨ 核心特性

### 🔍 信息提取能力
- **快速协议扫描** - 了解流量包基本情况
- **模式搜索** - 发现明显的线索和特征
- **字段提取** - 获取特定数据
- **编码检测** - 识别常见编码方式

### 🛠️ 14 个辅助工具

#### 侦察工具
1. **quick_analysis** - 快速侦察，提供初步线索
2. **search_in_packets** - 智能搜索，快速定位信息
3. **list_interfaces** - 列出网络接口

#### 数据获取工具
4. **analyze_pcap** - 获取数据包详情
5. **extract_fields** - 提取特定字段
6. **analyze_protocols** - 协议专项分析
7. **get_packet_statistics** - 统计信息
8. **get_protocols** - 协议列表

#### 高级功能
9. **export_objects** - 生成文件导出命令
10. **capture_live** - 实时抓包
11. **analyze_errors** - 错误检测

#### 安全工具
12. **check_threats** - 威胁检测（URLhaus）
13. **check_ip_threats** - IP 威胁查询
14. **extract_credentials** - 凭证提取

### 🚀 灵活的分析框架

- **MCP 提供信息** - 快速获取数据和线索
- **AI 自主决策** - 根据信息设计分析策略
- **tshark 深入分析** - 处理复杂场景
- **自定义脚本** - 解决特定问题

## 📦 安装

### 前置要求
- Python 3.8+
- Wireshark (需要 `tshark` 命令行工具)

### 安装步骤

```bash
# 克隆或下载项目
cd wireMCP-YE

# 安装依赖
pip install -r requirements.txt

# 验证 tshark 可用
tshark --version
```

## 🚀 快速开始

### 1. 启动服务器

```bash
# 使用默认配置
python wireshark_mcp.py

# 自定义配置
python wireshark_mcp.py --host 127.0.0.1 --port 3000
```

### 2. 配置 Cursor IDE

在项目根目录创建 `mcp.json`：

```json
{
  "mcpServers": {
    "wireshark": {
      "url": "http://127.0.0.1:3000/sse"
    }
  }
}
```

### 3. 访问状态页面

打开浏览器访问 http://127.0.0.1:3000

## 💡 使用理念

### 工具能做什么

✅ 快速协议扫描
✅ 搜索明显模式
✅ 提取特定字段
✅ 检测常见编码
✅ 提供初步线索

### 工具不能做什么

❌ 处理所有 CTF 题型
❌ 保证找到所有隐藏信息
❌ 自动解决复杂问题
❌ 替代深入手动分析

### AI 需要自己做什么

✅ 深入分析和推理
✅ 设计分析策略
✅ 编写自定义脚本
✅ 组合多种工具
✅ 尝试不同方法

## 📚 标准分析流程

综合提示词
```
分析 xxx.pcapng 提取 flag

步骤：
1. 使用 analyze_pcap 快速查看包信息
2. 根据协议类型，用 analyze_protocols 深入分析
3. 用 extract_fields 提取关键字段
4. 分析数据，编写脚本解码或使用 tshark 深入分析

注意：MCP 工具提供信息，你需要自己灵活分析和决策
```

### 第 1 步：快速侦察（使用 MCP）

```
quick_analysis("file.pcap")
→ 了解基本情况
→ 发现明显线索
→ 评估结果
```

### 第 2 步：针对性分析（MCP + 自定义）

```
根据线索：
- 编码数据 → 编写自定义解码脚本
- 协议流量 → 使用 tshark 深入分析
- 文件传输 → 导出并分析文件
```

### 第 3 步：深度挖掘（主要自定义）

```
没有明显发现时：
- 全面数据提取
- 自定义脚本分析
- tshark 高级功能
- 协议逆向
```

## 🎓 实战示例

### 示例 1：多层编码

```
步骤 1：MCP 侦察
quick_analysis("capture.pcap")
→ 返回：检测到 Base64 编码

步骤 2：AI 分析
思考：Base64 可能只是第一层

步骤 3：自定义脚本
编写脚本尝试多种解码组合：
- Base64 → Hex → ASCII
- Base64 → URL decode → Base64
- Base64 → ROT13

步骤 4：找到 Flag
经过多层解码找到：flag{multi_layer_encoding}
```

### 示例 2：TCP 流重组

```
步骤 1：MCP 侦察
analyze_protocols("capture.pcap", "tcp")
→ 返回：大量 TCP 数据包

步骤 2：AI 分析
思考：数据可能分散在多个包中

步骤 3：使用 tshark
tshark -r capture.pcap -q -z follow,tcp,ascii,0 > stream.txt

步骤 4：分析流数据
在重组的流中找到完整的 flag
```

### 示例 3：文件隐写

```
步骤 1：MCP 侦察
export_objects("capture.pcap", "http")
→ 导出了一张图片

步骤 2：AI 分析
思考：图片可能包含隐写信息

步骤 3：自定义分析
使用 steghide、binwalk 等工具分析图片

步骤 4：提取隐藏数据
从图片中提取出 flag
```

## 🔧 tshark 高级技巧

### 导出对象
```bash
tshark -r file.pcap --export-objects http,./output/
```

### 追踪 TCP 流
```bash
tshark -r file.pcap -z follow,tcp,ascii,0
tshark -r file.pcap -q -z follow,tcp,raw,0 > stream.bin
```

### 自定义字段提取
```bash
tshark -r file.pcap -T fields \
  -e frame.number -e ip.src -e tcp.payload \
  -E separator="|" -E quote=d
```

### 统计和分析
```bash
tshark -r file.pcap -q -z conv,tcp
tshark -r file.pcap -q -z endpoints,ip
tshark -r file.pcap -q -z io,phs
```

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
```

## 📊 工具定位对比

| 方面 | 传统 tshark | WireMCP-YE | AI 分析 |
|------|------------|------------|---------|
| 数据提取 | ✅ 强大 | ✅ 便捷 | - |
| 信息整合 | ❌ 需手动 | ✅ 自动 | - |
| 深入分析 | ✅ 灵活 | ⚠️ 有限 | ✅ 核心 |
| 问题解决 | - | - | ✅ 关键 |

## ⚠️ 重要提示

### 不要过度依赖 MCP

```
错误思维："MCP 没找到就没有"
正确思维："MCP 没找到明显的，我需要深入分析"
```

### 工具建议是参考

```
错误思维："工具生成了脚本，直接运行就行"
正确思维："工具生成的脚本是参考，我需要理解并改进"
```

### 思考比工具更重要

```
错误思维："再调用一次工具可能会有不同结果"
正确思维："工具已经给了我数据，我需要换个角度分析"
```

## 🔍 端点说明

| 端点 | 方法 | 描述 |
|-----|------|------|
| `/` | GET | 状态页面 |
| `/status` | GET | 服务器状态 |
| `/sse` | GET | SSE 长连接端点（MCP 客户端连接） |
| `/messages` | POST | JSON-RPC 消息接收端点 |

## 🐛 Bug 修复

### v1.1.0 修复
- ✅ 修复 Windows 编码问题（GBK → UTF-8）
- ✅ 修复文件路径问题（相对路径 → 绝对路径）
- ✅ 添加智能内容分析
- ✅ 明确工具定位为辅助工具

## 📚 相关文档

- [使用指南](USAGE_GUIDE.md) - 详细的使用说明
- [最终优化总结](FINAL_OPTIMIZATION_SUMMARY.md) - 工具定位和使用理念
- [贡献指南](CONTRIBUTING.md) - 如何贡献代码
- [更新日志](CHANGELOG.md) - 版本更新记录

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- Wireshark/tshark 团队
- URLhaus 威胁情报
- MCP 协议开发者
- 所有贡献者

## 💬 核心原则

**MCP 工具提供信息，AI 提供智慧**

**工具的建议是参考，不是命令**

**真正的分析能力来自理解和创造，不是执行和重复**

---

**快速开始**：`python wireshark_mcp.py` → 配置 Cursor → 用 MCP 获取信息 → AI 自主分析决策
