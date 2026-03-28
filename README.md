# ConvertX Bot 🚀

A production-grade Telegram bot for advanced file conversion — PDF, Word, images, and more.

## Features

| Tool | Description |
|---|---|
| 📄 PDF → Word | Convert PDF to editable DOCX |
| 📝 Word → PDF | Convert DOCX to PDF |
| 🖼 Image → PDF | Convert JPG/PNG/WEBP to PDF |
| 🗂 Merge Images | Combine multiple images into a single PDF |
| ✂️ Split PDF | Split PDF into individual pages (ZIP) |
| 📦 Compress PDF | Reduce PDF file size |
| 🖼 Extract Images | Extract all images from a PDF (ZIP) |
| 📸 PDF → Images | Convert each PDF page to PNG (ZIP) |

**Additional features:** auto-detect file type, per-user rate limiting, async job queue, cancel support, concurrent multi-user handling.

---

## Quick Start (Local)

### 1. Clone & install

```bash
cd Fileforge
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your BOT_TOKEN from @BotFather
```

### 3. Run

```bash
python -m bot.main
```

---

## Deployment

### Docker

```bash
docker build -t convertx-bot .
docker run -d --name convertx-bot --env-file .env convertx-bot
```

### VPS (Ubuntu + systemd)

1. Install Python 3.11+ and system deps:
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv libmagic1 -y
```

2. Set up the project:
```bash
cd /opt
sudo git clone <your-repo-url> convertx-bot
cd convertx-bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # Add your BOT_TOKEN
```

3. Create a systemd service:
```bash
sudo nano /etc/systemd/system/convertx-bot.service
```

Paste:
```ini
[Unit]
Description=ConvertX Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/convertx-bot
EnvironmentFile=/opt/convertx-bot/.env
ExecStart=/opt/convertx-bot/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. Enable & start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable convertx-bot
sudo systemctl start convertx-bot
sudo systemctl status convertx-bot
```

---

## Project Structure

```
bot/
├── main.py                 # Entry point
├── config.py               # Environment vars, constants, logging
├── handlers/
│   ├── start_handler.py    # /start command, menus
│   ├── callback_handler.py # Inline keyboard router
│   ├── conversion_handlers.py # All conversion workflows
│   └── error_handler.py    # Global error handler
└── utils/
    ├── file_utils.py       # MIME detection, validation, cleanup
    ├── converter.py        # All conversion functions
    ├── rate_limiter.py     # Per-user rate limiting
    └── queue_manager.py    # Async job queue
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | Telegram bot token from @BotFather |
| `RATE_LIMIT_MAX_OPS` | ❌ | 10 | Max operations per window |
| `RATE_LIMIT_WINDOW` | ❌ | 60 | Rate limit window in seconds |
| `MAX_WORKERS` | ❌ | 3 | Queue worker pool size |
| `LOG_DIR` | ❌ | logs | Log file directory |

## Security

- Bot token loaded from environment variables only
- MIME-based file type validation
- Max file size enforcement (20 MB)
- Temp files cleaned immediately after processing
- No arbitrary command execution

## License

MIT
