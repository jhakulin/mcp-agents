# MCP Agents

A modular suite of **Model Context Protocol (MCP) agents** for YouTube video processing — including transcript extraction, AI-powered summarization, and channel monitoring. Compatible with **Claude Desktop** and any MCP client.

---

## 🚀 Features

- **YouTube Transcript Extraction:** Retrieve transcripts from any public YouTube video.
- **AI Summarization:** Generate smart summaries using OpenAI GPT models.
- **YouTube Channel Monitoring:** Track and monitor activity on multiple channels.
- **MCP Protocol Support:** Works out-of-the-box with all MCP-compatible tooling.
- **Extensible Agent System:** Easily add and customize agents for new tasks.

---

## 📋 Prerequisites

- **Python** 3.8 or higher  
- **PowerShell** (Windows) or **Terminal** (macOS/Linux)
- API keys:  
  - `OPENAI_API_KEY` for text summarization  
  - `YOUTUBE_API_KEY` (YouTube Data API v3) for channel features

---

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/jhakulin/mcp-agents.git
cd mcp-agents
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Activate:
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

On Windows (PowerShell):
```powershell
$env:OPENAI_API_KEY = "<your_openai_key>"
$env:YOUTUBE_API_KEY = "<your_youtube_key>"
```

On macOS/Linux (bash):
```bash
export OPENAI_API_KEY="<your_openai_key>"
export YOUTUBE_API_KEY="<your_youtube_key>"
```

---

## 🏃 Usage

### Run the server in local development mode

```bash
python server.py
```

### Or use MCP Inspector (web interface)

```bash
mcp dev server.py

# If you run into issues with "uv":
# (Windows PowerShell)
$env:MCP_SKIP_UV = "1"
mcp dev server.py

# (macOS/Linux bash)
export MCP_SKIP_UV="1"
mcp dev server.py
```

### Test the server

In a new terminal (with venv activated and env vars set):

```bash
python client.py
```

---

## 🧰 Available Tools

| Tool Name                     | Description                                  | Required API Keys            |
|-------------------------------|----------------------------------------------|------------------------------|
| `youtube_transcribe`          | Extract transcript from a YouTube video      | None                         |
| `summarize_text`              | Generate AI summary of given text            | `OPENAI_API_KEY`             |
| `youtube_channels_monitor`    | Monitor activity on multiple channels        | `YOUTUBE_API_KEY`            |
| `youtube_channel_latest`      | Fetch latest video(s) from a channel         | `YOUTUBE_API_KEY`            |
| `youtube_summarize_latest`    | Get and summarize channel’s latest videos    | Both (`OPENAI_API_KEY` and `YOUTUBE_API_KEY`) |
| `health_check`                | Check server status and configuration        | None                         |

---

## 📚 Documentation

- See [docs/](docs/) for API references and examples.  
- The [MCP Protocol](https://github.com/modelcontext/protocol) defines interoperability details.

---

## 🤝 Contributing

Pull requests and new agents are welcome! Please open an [issue](https://github.com/jhakulin/mcp-agents/issues) to discuss major changes.

---

## ⚖️ License

[MIT License](LICENSE)

---