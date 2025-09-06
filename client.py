"""Test client for YouTube Tools MCP server."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_youtube_tools():
    """Test the YouTube tools MCP server."""
    # Define server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env={
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
            "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY", "")
        }
    )
    
    print("Connecting to YouTube Tools MCP Server...")
    
    # Connect to the server
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()
            
            print("✅ Connected to YouTube Tools MCP Server\n")
            
            # 1. List available tools
            tools_result = await session.list_tools()
            print("Available tools:")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}")
            print()
            
            # 2. Check server health
            print("📋 Checking server health...")
            health = await session.call_tool("health_check", arguments={})
            health_data = json.loads(health.content[0].text)
            print(f"Status: {health_data['status']}")
            print(f"API Keys configured: {health_data['apis_configured']}\n")
            
            # Rest of the test code remains the same...


async def main():
    """Run the test client."""
    print("YouTube Tools MCP Client")
    print("=" * 60)
    
    # Check for environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set - summarization will not work")
    if not os.environ.get("YOUTUBE_API_KEY"):
        print("⚠️  Warning: YOUTUBE_API_KEY not set - channel monitoring will not work")
    
    print("\nStarting test...\n")
    
    try:
        await test_youtube_tools()
        print("\n✅ All tests completed!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())