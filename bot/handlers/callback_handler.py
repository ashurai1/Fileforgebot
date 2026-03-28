"""
ConvertX Bot - Callback Query Router
Central dispatcher for all inline keyboard button presses.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import logger
from bot.handlers.start_handler import show_main_menu, show_more_tools
from bot.handlers.conversion_handlers import (
    prompt_pdf_to_word,
    prompt_word_to_pdf,
    prompt_img_to_pdf,
    prompt_merge_images,
    prompt_compress_pdf,
    prompt_split_pdf,
    prompt_extract_images,
    prompt_pdf_to_images,
    handle_merge_done,
    handle_cancel,
)

# ═══════════════════════════════════════════════════════════════════════════
# Callback routing map
# ═══════════════════════════════════════════════════════════════════════════

CALLBACK_MAP = {
    # Main menu tools
    "pdf_to_word": prompt_pdf_to_word,
    "word_to_pdf": prompt_word_to_pdf,
    "img_to_pdf": prompt_img_to_pdf,
    "merge_images": prompt_merge_images,
    "compress_pdf": prompt_compress_pdf,

    # More tools
    "split_pdf": prompt_split_pdf,
    "extract_images": prompt_extract_images,
    "pdf_to_images": prompt_pdf_to_images,

    # Navigation
    "more_tools": show_more_tools,
    "back_main": show_main_menu,

    # Actions
    "merge_done": handle_merge_done,
    "cancel": handle_cancel,
}


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Route callback queries to the appropriate handler function
    based on the callback_data string.
    """
    query = update.callback_query
    data = query.data

    logger.debug(
        "Callback from user %s: %s",
        update.effective_user.id,
        data,
    )

    handler = CALLBACK_MAP.get(data)
    if handler:
        await handler(update, context)
    else:
        logger.warning("Unknown callback_data: %s", data)
        await query.answer("❓ Unknown action.", show_alert=True)
