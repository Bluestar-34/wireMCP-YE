"""
WireMCP-YE - Unified Wireshark MCP Server

A Model Context Protocol server for network packet analysis using Wireshark/tshark.
"""

__version__ = "1.0.0"
__author__ = "WireMCP-YE Contributors"

from .main import main
from .server import SSEMCPServer
from .wireshark import WiresharkMCP

__all__ = [
    "main",
    "SSEMCPServer",
    "WiresharkMCP",
]


