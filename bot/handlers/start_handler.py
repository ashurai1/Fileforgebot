"""
ConvertX Bot - Start Handler
Handles the /start command and renders the main menu with inline keyboards.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.config import logger

# ═══════════════════════════════════════════════════════════════════════════
# Menu Keyboards
# ═══════════════════════════════════════════════════════════════════════════

MAIN_MENU_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("📄 PDF → Word", callback_data="pdf_to_word"),
            InlineKeyboardButton("📝 Word → PDF", callback_data="word_to_pdf"),
        ],
        [
            InlineKeyboardButton("🖼 Image → PDF", callback_data="img_to_pdf"),
            InlineKeyboardButton("🗂 Merge Images", callback_data="merge_images"),
        ],
        [
            InlineKeyboardButton("📦 Compress PDF", callback_data="compress_pdf"),
            InlineKeyboardButton("🔧 More Tools", callback_data="more_tools"),
        ],
    ]
)

MORE_TOOLS_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("✂️ Split PDF", callback_data="split_pdf"),
            InlineKeyboardButton("🖼 Extract Images", callback_data="extract_images"),
        ],
        [
            InlineKeyboardButton("📸 PDF → Images", callback_data="pdf_to_images"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="back_main"),
        ],
    ]
)

# ═══════════════════════════════════════════════════════════════════════════
# Welcome message
# ═══════════════════════════════════════════════════════════════════════════

WELCOME_TEXT = (
    "👋 <b>Welcome to ashwani bot</b> 🚀\n\n"
    "Your all-in-one file conversion tool.\n\n"
    "Choose a tool below to get started:"
)


# ═══════════════════════════════════════════════════════════════════════════
# Handlers
# ═══════════════════════════════════════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command — show the main menu."""
    user = update.effective_user
    logger.info("User %s (%s) started the bot", user.id, user.full_name)

    # Reset any user-specific conversation state
    context.user_data.clear()

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show or return to the main menu (used from callbacks)."""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.message.text:
            await query.edit_message_text(
                WELCOME_TEXT,
                parse_mode="HTML",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
        else:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                WELCOME_TEXT,
                parse_mode="HTML",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
    except Exception as e:
        logger.error("Failed to show main menu: %s", e)
        await query.message.reply_text(
            WELCOME_TEXT,
            parse_mode="HTML",
            reply_markup=MAIN_MENU_KEYBOARD,
        )


async def show_more_tools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the 'More Tools' sub-menu."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔧 <b>More Tools</b>\n\nSelect a tool:",
        parse_mode="HTML",
        reply_markup=MORE_TOOLS_KEYBOARD,
    )
