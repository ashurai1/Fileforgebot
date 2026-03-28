"""
ConvertX Bot - Global Error Handler
Catches all unhandled exceptions and sends user-friendly messages.
"""

import html
import traceback

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import logger


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global error handler. Logs the full traceback and sends a
    user-friendly error message if possible.
    """
    # Log the full error
    logger.error(
        "Exception while handling an update:",
        exc_info=context.error,
    )

    # Build a developer-readable traceback
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb_string = "".join(tb_list)
    logger.error("Full traceback:\n%s", tb_string)

    # Determine a user-friendly message
    error_type = type(context.error).__name__
    error_messages = {
        "NetworkError": "⚠️ Network issue. Please try again in a moment.",
        "TimedOut": "⏰ The operation timed out. Please try again.",
        "BadRequest": "❌ Something went wrong with the request. Please try a different file.",
        "Forbidden": "🚫 I don't have permission to perform this action.",
    }
    user_message = error_messages.get(
        error_type,
        "❌ An unexpected error occurred. Please try again later.",
    )

    # Try to notify the user
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(user_message)
        except Exception:
            logger.error("Failed to send error message to user")

    # If caused by a callback query, answer it
    if isinstance(update, Update) and update.callback_query:
        try:
            await update.callback_query.answer(
                "❌ An error occurred.", show_alert=True
            )
        except Exception:
            pass
