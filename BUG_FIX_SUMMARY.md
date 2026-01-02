# Bug 修复总结

## 修复的问题

### Bug 1: 文件路径问题
**错误信息**: `tshark: The file "flag.pcap" doesn't exist.`

**原因**: 
- 当用户提供相对路径时，tshark 可能无法正确解析文件位置
- 特别是在 MCP 服务器运行在不同工作目录时

**修复方案**:
- 在所有接受 `file_path` 参数的函数中，使用 `os.path.abspath()` 将相对路径转换为绝对路径
- 修改的函数：
  - `analyze_pcap()`
  - `get_packet_statistics()`
  - `extract_fields()`
  - `analyze_protocols()`
  - `analyze_errors()`
  - `extract_credentials()`

### Bug 2: Windows 编码问题
**错误信息**: 
```
UnicodeDecodeError: 'gbk' codec can't decode byte 0xad in position 241: illegal multibyte sequence
```

**原因**:
- Windows 系统默认使用 GBK 编码
- `subprocess.run()` 在 Windows 上默认使用系统编码（GBK）解码输出
- tshark 输出的二进制数据包含无法用 GBK 解码的字节

**修复方案**:
- 在所有 `subprocess.run()` 调用中添加 `encoding='utf-8'` 和 `errors='replace'` 参数
- `encoding='utf-8'`: 强制使用 UTF-8 编码
- `errors='replace'`: 遇到无法解码的字节时用替换字符代替，而不是抛出异常

**修改的函数**:
- `_run_tshark_command()`
- `_get_tshark_version()`
- `list_interfaces()`
- `get_protocols()`
- `check_threats()` 中的 IP 提取部分
- `extract_credentials()` 中的两个 tshark 调用

## 测试建议

1. **文件路径测试**:
   ```python
   # 测试相对路径
   analyze_pcap("flag.pcap")
   
   # 测试绝对路径
   analyze_pcap("C:/path/to/flag.pcap")
   
   # 测试当前目录
   analyze_pcap("./flag.pcap")
   ```

2. **编码测试**:
   - 使用包含非 ASCII 字符的 pcap 文件
   - 在 Windows 系统上运行所有工具函数
   - 验证不再出现 UnicodeDecodeError

## 代码变更示例

### 修复前:
```python
def analyze_pcap(self, file_path: str, filter: str = "", max_packets: int = 100) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件: {file_path}")
    cmd = [self.tshark_path, "-r", file_path, "-T", "json", "-c", str(max_packets)]
    # ...
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
```

### 修复后:
```python
def analyze_pcap(self, file_path: str, filter: str = "", max_packets: int = 100) -> str:
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"找不到文件: {abs_path} (原始路径: {file_path})")
    cmd = [self.tshark_path, "-r", abs_path, "-T", "json", "-c", str(max_packets)]
    # ...
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
```

## 影响范围

- ✅ 所有文件读取操作现在支持相对路径和绝对路径
- ✅ 所有 subprocess 调用在 Windows 上不再出现编码错误
- ✅ 错误信息更详细，同时显示原始路径和解析后的绝对路径
- ✅ 向后兼容，不影响现有功能
