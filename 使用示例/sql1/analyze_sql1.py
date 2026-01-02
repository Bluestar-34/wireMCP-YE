#!/usr/bin/env python3
"""
使用 Wireshark MCP 工具分析 sql1.pcapng 文件
"""
import json
import httpx
import asyncio
import sys

async def call_mcp_tool(tool_name: str, arguments: dict):
    """通过 MCP 服务器调用工具"""
    # 首先建立 SSE 连接获取 session_id
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 建立 SSE 连接
        async with client.stream("GET", "http://127.0.0.1:3000/sse") as sse_response:
            session_id = None
            async for line in sse_response.aiter_lines():
                if line.startswith("event: endpoint"):
                    # 解析 endpoint 获取 session_id
                    next_line = await sse_response.aiter_lines().__anext__()
                    if next_line.startswith("data: "):
                        endpoint = next_line[6:]  # 去掉 "data: "
                        session_id = endpoint.split("session_id=")[1] if "session_id=" in endpoint else None
                        break
            
            if not session_id:
                print("无法获取 session_id")
                return None
            
            # 构造 tools/call 请求
            message = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # 发送消息
            response = await client.post(
                f"http://127.0.0.1:3000/messages?session_id={session_id}",
                json=message
            )
            
            if response.status_code != 200:
                print(f"请求失败: {response.status_code}")
                print(response.text)
                return None
            
            # 等待响应（通过 SSE）
            async for line in sse_response.aiter_lines():
                if line.startswith("event: message"):
                    next_line = await sse_response.aiter_lines().__anext__()
                    if next_line.startswith("data: "):
                        data = json.loads(next_line[6:])
                        if data.get("id") == "1":
                            return data
            
            return None

async def main():
    file_path = "sql1.pcapng"
    
    print("=" * 60)
    print("使用 Wireshark MCP 工具分析 sql1.pcapng")
    print("=" * 60)
    
    # 1. 先分析协议统计
    print("\n[1] 获取数据包统计信息...")
    try:
        result = await call_mcp_tool("get_packet_statistics", {
            "file_path": file_path
        })
        if result and "result" in result:
            print(result["result"]["content"][0]["text"][:2000])
    except Exception as e:
        print(f"错误: {e}")
    
    # 2. 分析 pcap 文件
    print("\n[2] 分析 pcap 文件（查找 SQL 相关数据包）...")
    try:
        result = await call_mcp_tool("analyze_pcap", {
            "file_path": file_path,
            "filter": "mysql or tcp.port == 3306",
            "max_packets": 100
        })
        if result and "result" in result:
            text = result["result"]["content"][0]["text"]
            print(text[:5000])  # 打印前5000字符
    except Exception as e:
        print(f"错误: {e}")
    
    # 3. 提取 MySQL 查询字段
    print("\n[3] 提取 MySQL 查询字段...")
    try:
        result = await call_mcp_tool("extract_fields", {
            "file_path": file_path,
            "fields": ["mysql.query", "frame.number", "ip.src", "ip.dst"],
            "filter": "mysql",
            "max_packets": 1000
        })
        if result and "result" in result:
            print(result["result"]["content"][0]["text"][:5000])
    except Exception as e:
        print(f"错误: {e}")
    
    # 4. 提取凭证（可能包含 flag）
    print("\n[4] 提取凭证信息...")
    try:
        result = await call_mcp_tool("extract_credentials", {
            "file_path": file_path
        })
        if result and "result" in result:
            print(result["result"]["content"][0]["text"])
    except Exception as e:
        print(f"错误: {e}")
    
    # 5. 提取所有文本字段，查找 flag
    print("\n[5] 提取所有可能的文本字段，查找 flag...")
    try:
        result = await call_mcp_tool("extract_fields", {
            "file_path": file_path,
            "fields": ["frame.number", "data.text", "tcp.payload", "udp.payload"],
            "filter": "tcp or udp",
            "max_packets": 5000
        })
        if result and "result" in result:
            text = result["result"]["content"][0]["text"]
            # 查找 flag
            if "flag" in text.lower():
                print("找到包含 'flag' 的内容:")
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if "flag" in line.lower():
                        print(f"  {line}")
                        # 打印前后几行
                        for j in range(max(0, i-2), min(len(lines), i+3)):
                            if j != i:
                                print(f"    {lines[j]}")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())

