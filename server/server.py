"""FastMCP server for YouTube tools."""

import os
import sys
import logging
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP(
    name="YouTubeTools",
    host="0.0.0.0",  # only used for SSE transport
    port=8080,  # only used for SSE transport
    stateless_http=True,
)

# Import tools to register them with the server
from . import tools  # This will execute the @mcp.tool() decorators


def main():
    """Main entry point for the MCP server."""
    # Check for required environment variables
    required_vars = ["OPENAI_API_KEY", "YOUTUBE_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.info("Some tools may not work without these API keys.")
    
    # Get transport from environment or default to stdio
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    # Run with specified transport
    logger.info("Starting YouTube Tools MCP Server")
    logger.info("=" * 60)
    logger.info("Available tools:")
    logger.info("  - youtube_transcribe: Extract YouTube video transcripts")
    logger.info("  - summarize_text: Summarize text using AI")
    logger.info("  - youtube_channels_monitor: Monitor YouTube channels")
    logger.info("  - youtube_channel_latest: Get latest video from channel")
    logger.info("  - youtube_summarize_latest: Get and summarize latest videos")
    logger.info("  - health_check: Check server health status")
    logger.info("=" * 60)
    
    if transport == "stdio":
        logger.info("Running server with stdio transport")
        mcp.run(transport="stdio")
    elif transport == "sse":
        logger.info(f"Running server with SSE transport")
        mcp.run(transport="sse")
    elif transport == "streamable-http":
        logger.info("Running server with Streamable HTTP transport")
        mcp.run(transport="streamable-http")
    else:
        raise ValueError(f"Unknown transport: {transport}")


if __name__ == "__main__":
    main()