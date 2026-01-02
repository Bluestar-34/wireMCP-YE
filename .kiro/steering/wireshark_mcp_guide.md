---
inclusion: always
---

# Wireshark MCP 工具使用指南

## 核心理念：MCP 是辅助工具，不是完整解决方案

⚠️ **重要认知**：
- MCP 工具**无法覆盖所有流量分析场景**
- MCP 工具的作用是**提供信息和线索**，而不是直接给出答案
- AI 需要**根据 MCP 返回的信息，自主决策后续操作**
- 真正的分析能力来自 AI 的推理和创造性思维

## 正确的工作流程

```
MCP 工具 → 获取信息 → AI 分析判断 → AI 自主决策 → 执行操作 → 解决问题
   ↑                                        ↓
   └────────────── 必要时再次使用 MCP ──────────┘
```

## 工具定位

### 1. quick_analysis - 快速侦察工具

**作用**：
- 快速了解流量包的基本情况
- 发现明显的线索和特征
- 提供初步的分析方向

**不是**：
- ❌ 不是完整的解题工具
- ❌ 不能保证找到所有 flag
- ❌ 不能处理所有类型的题目

**使用后 AI 应该**：
- ✅ 分析返回的信息，形成自己的判断
- ✅ 根据线索设计自己的分析策略
- ✅ 决定是否需要编写自定义脚本
- ✅ 决定是否需要使用 tshark 或其他工具

**示例**：
```
quick_analysis 返回：检测到 Base64 编码

AI 不应该：
❌ 只执行工具生成的脚本就结束

AI 应该：
✅ 思考：Base64 可能是什么？
✅ 判断：需要解码，但可能还有其他编码层
✅ 决策：编写更全面的解码脚本，尝试多种解码方式
✅ 执行：运行自己编写的脚本
✅ 分析：如果没找到，继续深入分析
```

### 2. search_in_packets - 信息提取工具

**作用**：
- 快速搜索特定模式
- 提取可能的关键信息

**不是**：
- ❌ 不能保证找到所有相关信息
- ❌ 搜索模式可能不够全面

**使用后 AI 应该**：
- ✅ 评估搜索结果的质量
- ✅ 考虑是否需要调整搜索模式
- ✅ 决定是否需要更复杂的分析

### 3. analyze_pcap / extract_fields - 数据获取工具

**作用**：
- 获取原始数据包信息
- 提取特定字段

**不是**：
- ❌ 不会自动分析数据含义
- ❌ 不会告诉你数据如何使用

**使用后 AI 应该**：
- ✅ 仔细分析提取的数据
- ✅ 寻找数据之间的关联
- ✅ 设计自己的分析方法

## AI 自主决策的关键场景

### 场景 1：MCP 工具没有找到明显线索

```
quick_analysis 返回：no_obvious_findings

错误做法：
❌ 放弃或重复调用工具

正确做法：
✅ 使用 extract_fields 提取所有可能的文本数据
✅ 编写 Python 脚本分析提取的数据
✅ 使用 tshark 进行更深入的分析
✅ 尝试不同的协议过滤器
✅ 分析数据包的时序关系
✅ 查找异常的数据包大小或模式
```

### 场景 2：发现了线索但不完整

```
search_in_packets 找到：部分 Base64 数据

错误做法：
❌ 只解码找到的数据就结束

正确做法：
✅ 思考：可能有多段数据需要拼接
✅ 使用 extract_fields 提取完整的数据流
✅ 编写脚本按顺序重组数据
✅ 尝试不同的解码方式（Base64, Hex, URL编码等）
✅ 分析解码后的数据是否还有其他编码层
```

### 场景 3：需要协议级别的深入分析

```
analyze_protocols 显示：HTTP 流量

错误做法：
❌ 只看 MCP 返回的数据包

正确做法：
✅ 使用 tshark 导出 HTTP 对象
✅ 分析 HTTP 会话的完整流程
✅ 重放 HTTP 请求
✅ 分析 Cookie 和 Session
✅ 检查 HTTP 响应头中的隐藏信息
✅ 编写脚本模拟客户端行为
```

### 场景 4：需要跨数据包的关联分析

```
MCP 工具返回：多个数据包的信息

错误做法：
❌ 单独分析每个数据包

正确做法：
✅ 分析数据包之间的时序关系
✅ 查找 TCP 流的完整会话
✅ 重组分片的数据
✅ 分析请求-响应对应关系
✅ 使用 tshark 的 follow stream 功能
✅ 编写脚本提取和重组完整的数据流
```

## 自定义脚本编写指南

### 何时需要编写自定义脚本

1. **MCP 工具的输出需要进一步处理**
   - 数据需要解码、解密、重组
   - 需要复杂的模式匹配
   - 需要数学计算或算法处理

2. **需要组合多个工具的结果**
   - 从多个 MCP 调用中整合信息
   - 结合 tshark 和 Python 分析

3. **需要自动化重复操作**
   - 批量处理数据包
   - 尝试多种解码方式
   - 暴力破解或枚举

### 脚本编写建议

```python
#!/usr/bin/env python3
"""
自定义流量分析脚本

思路：
1. 从 MCP 工具获取的信息：...
2. 发现的问题：...
3. 解决方案：...
"""

import base64
import re
import subprocess
from urllib.parse import unquote

# 步骤 1：使用 tshark 提取原始数据
def extract_data():
    cmd = ["tshark", "-r", "file.pcap", "-T", "fields", "-e", "data.text"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    return result.stdout.split('\n')

# 步骤 2：多层解码
def decode_data(data):
    # 尝试 URL 解码
    decoded = unquote(data)
    
    # 尝试 Base64 解码
    try:
        decoded = base64.b64decode(decoded)
    except:
        pass
    
    # 尝试 Hex 解码
    try:
        decoded = bytes.fromhex(decoded.decode())
    except:
        pass
    
    return decoded

# 步骤 3：模式匹配
def find_flag(data):
    patterns = [
        r'flag\{[^}]+\}',
        r'FLAG\{[^}]+\}',
        r'ctf\{[^}]+\}',
        # 添加更多模式
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, str(data), re.IGNORECASE)
        if matches:
            return matches
    
    return None

# 主逻辑
def main():
    print("=== 自定义流量分析 ===\n")
    
    # 提取数据
    raw_data = extract_data()
    
    # 处理每条数据
    for item in raw_data:
        if not item.strip():
            continue
        
        # 解码
        decoded = decode_data(item)
        
        # 查找 flag
        flag = find_flag(decoded)
        if flag:
            print(f"找到 FLAG: {flag}")
            return
    
    print("未找到 flag，需要进一步分析")

if __name__ == "__main__":
    main()
```

## 使用 tshark 的高级技巧

### 1. 导出对象
```bash
# 导出 HTTP 对象
tshark -r file.pcap --export-objects http,./output/

# 导出 SMB 文件
tshark -r file.pcap --export-objects smb,./output/
```

### 2. 追踪 TCP 流
```bash
# 追踪特定流
tshark -r file.pcap -z follow,tcp,ascii,0

# 导出流数据
tshark -r file.pcap -q -z follow,tcp,raw,0 > stream.bin
```

### 3. 自定义字段提取
```bash
# 提取多个字段并格式化
tshark -r file.pcap -T fields \
  -e frame.number \
  -e ip.src \
  -e ip.dst \
  -e tcp.payload \
  -E separator="|" \
  -E quote=d
```

### 4. 统计和分析
```bash
# 会话统计
tshark -r file.pcap -q -z conv,tcp

# 端点统计
tshark -r file.pcap -q -z endpoints,ip

# 协议层次
tshark -r file.pcap -q -z io,phs
```

## 避免的陷阱

### ❌ 陷阱 1：过度依赖 MCP 工具

```
错误思维：
"MCP 工具没找到 flag，那就没有 flag"

正确思维：
"MCP 工具没找到明显的 flag，我需要深入分析"
```

### ❌ 陷阱 2：忽略工具的局限性

```
错误思维：
"quick_analysis 说没有明显发现，那就放弃"

正确思维：
"quick_analysis 只是初步扫描，我需要更深入的分析"
```

### ❌ 陷阱 3：不思考直接执行

```
错误思维：
"工具生成了脚本，直接运行就行"

正确思维：
"工具生成的脚本是参考，我需要理解并可能改进它"
```

### ❌ 陷阱 4：重复无效操作

```
错误思维：
"再调用一次 analyze_pcap 可能会有不同结果"

正确思维：
"analyze_pcap 已经给了我数据，我需要换个角度分析"
```

## 标准分析流程（推荐）

### 第 1 步：快速侦察（使用 MCP）

```
1. quick_analysis("file.pcap")
   → 了解基本情况、协议分布、明显特征

2. 评估结果：
   - 找到 flag？→ 验证并报告
   - 有明显线索？→ 进入第 2 步
   - 没有线索？→ 进入第 3 步
```

### 第 2 步：针对性分析（MCP + 自定义）

```
根据第 1 步的线索：

如果是编码数据：
- 使用 extract_fields 提取完整数据
- 编写自定义解码脚本
- 尝试多种解码方式

如果是协议流量：
- 使用 analyze_protocols 深入分析
- 使用 tshark 导出对象或追踪流
- 分析协议的完整交互过程

如果是文件传输：
- 使用 export_objects 导出文件
- 分析文件内容
- 检查文件元数据
```

### 第 3 步：深度挖掘（主要靠自定义）

```
当 MCP 工具没有明显发现时：

1. 全面数据提取：
   extract_fields(file_path, ["data.text", "tcp.payload", "udp.payload"])

2. 自定义脚本分析：
   - 编写 Python 脚本处理提取的数据
   - 尝试各种解码、解密方式
   - 查找隐藏的模式

3. 使用 tshark 高级功能：
   - 追踪 TCP/UDP 流
   - 导出所有对象
   - 分析时序和关联

4. 协议逆向：
   - 分析未知协议的结构
   - 重组分片数据
   - 模拟协议交互
```

## 实战示例

### 示例 1：多层编码的 Flag

```
步骤 1：MCP 侦察
quick_analysis("capture.pcap")
→ 返回：检测到 Base64 编码

步骤 2：AI 分析
思考：Base64 可能只是第一层，可能还有其他编码

步骤 3：自定义脚本
编写脚本尝试：
- Base64 → Hex → ASCII
- Base64 → URL decode → Base64
- Base64 → ROT13
- Base64 → XOR

步骤 4：找到 Flag
经过多层解码找到：flag{multi_layer_encoding}
```

### 示例 2：TCP 流重组

```
步骤 1：MCP 侦察
analyze_protocols("capture.pcap", "tcp")
→ 返回：大量 TCP 数据包

步骤 2：AI 分析
思考：数据可能分散在多个包中，需要重组

步骤 3：使用 tshark
tshark -r capture.pcap -q -z follow,tcp,ascii,0 > stream.txt

步骤 4：分析流数据
在重组的流中找到完整的 flag
```

### 示例 3：隐写术

```
步骤 1：MCP 侦察
export_objects("capture.pcap", "http")
→ 导出了一张图片

步骤 2：AI 分析
思考：图片可能包含隐写信息

步骤 3：自定义分析
使用 steghide、binwalk、strings 等工具分析图片

步骤 4：提取隐藏数据
从图片中提取出 flag
```

## 总结

### 核心原则

1. **MCP 是起点，不是终点**
   - 用 MCP 快速了解情况
   - 用 AI 深入分析和决策
   - 用自定义方法解决问题

2. **思考比工具更重要**
   - 理解数据的含义
   - 推理可能的隐藏方式
   - 设计针对性的分析策略

3. **灵活组合各种工具**
   - MCP 工具
   - tshark 命令
   - Python 脚本
   - 其他分析工具

4. **持续迭代和深入**
   - 不要满足于表面信息
   - 不断尝试新的分析角度
   - 从失败中学习和调整

### 记住

- MCP 工具提供**信息**，AI 提供**智慧**
- 工具的建议是**参考**，不是**命令**
- 真正的分析能力来自**理解和创造**，不是**执行和重复**
