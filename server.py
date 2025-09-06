"""Main entry point for MCP server - can be run with `mcp dev server.py` or `mcp run server.py`."""

import os
import sys
import logging
from pathlib import Path

# Add current directory to Python path to ensure local mcp module is found
sys.path.insert(0, str(Path(__file__).parent))

# Import from local mcp package (not the installed mcp package)
from server.server import main

# The tools are automatically registered when the tools module is imported
import server.tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check environment on import
required_vars = ["OPENAI_API_KEY", "YOUTUBE_API_KEY"]
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
    logger.info("Some tools may not work without these API keys.")

logger.info("YouTube Tools MCP Server ready")
logger.info("Run with: mcp dev server.py (for inspector) or mcp run server.py")

# Execute main when run directly
if __name__ == "__main__":
    main()