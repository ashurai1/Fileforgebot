"""
ConvertX Bot - Main Entry Point
Builds the Application, registers all handlers, and starts polling.
"""

import asyncio
import signal

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot.config import BOT_TOKEN, logger
from bot.handlers.start_handler import start_command
from bot.handlers.callback_handler import callback_router
from bot.handlers.conversion_handlers import handle_file_upload
from bot.handlers.error_handler import error_handler
from bot.utils.file_utils import cleanup_temp_dir
from bot.utils.queue_manager import queue_manager


async def post_init(application: Application) -> None:
    """Called after the Application is initialized — start the queue manager."""
    await queue_manager.start()
    logger.info("ConvertX Bot is online! 🚀")


async def post_shutdown(application: Application) -> None:
    """Called on shutdown — stop queue and clean temp files."""
    await queue_manager.stop()
    cleanup_temp_dir()
    logger.info("ConvertX Bot shut down gracefully.")


import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")
    
    def log_message(self, format, *args):
        pass  # Suppress health check logs

def start_healthcheck_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info("Starting healthcheck server on port %s", port)
    server.serve_forever()

def main() -> None:
    """Build and run the bot."""
    logger.info("Starting ConvertX Bot...")

    # Start the dummy web server for Render health checks
    threading.Thread(target=start_healthcheck_server, daemon=True).start()

    # Build the application
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)  # handle multiple users at once
        .build()
    )

    # ── Command handlers ─────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))

    # ── Callback query handler (inline keyboard buttons) ─────────────────
    app.add_handler(CallbackQueryHandler(callback_router))

    # ── Document / photo handler ─────────────────────────────────────────
    app.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.PHOTO,
            handle_file_upload,
        )
    )

    # ── Global error handler ─────────────────────────────────────────────
    app.add_error_handler(error_handler)

    # ── Start polling ────────────────────────────────────────────────────
    logger.info("Bot is polling for updates...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    main()
