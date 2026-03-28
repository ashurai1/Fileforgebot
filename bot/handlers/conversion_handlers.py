"""
ConvertX Bot - Conversion Handlers
Manages the full user flow for each conversion type:
  prompt → file upload → processing → result delivery → cleanup
"""

from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.config import logger
from bot.utils.file_utils import (
    validate_file_size,
    validate_file_type,
    get_temp_path,
    auto_rename,
    cleanup_files,
)
from bot.utils.converter import (
    pdf_to_docx,
    docx_to_pdf,
    image_to_pdf,
    merge_images_to_pdf,
    split_pdf,
    compress_pdf,
    extract_images_from_pdf,
    pdf_to_images,
)
from bot.utils.rate_limiter import rate_limiter
from bot.utils.queue_manager import queue_manager
from bot.handlers.start_handler import MAIN_MENU_KEYBOARD


# ═══════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════════

CANCEL_KEYBOARD = InlineKeyboardMarkup(
    [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
)

DONE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("✅ Done — Merge Now", callback_data="merge_done"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ]
    ]
)


async def _check_rate_limit(update: Update, user_id: int) -> bool:
    """Check rate limit and notify user if exceeded. Returns True if OK."""
    if not rate_limiter.is_allowed(user_id):
        await update.effective_message.reply_text(
            "⚠️ <b>Rate limit exceeded</b>.\n"
            "Please wait a minute before trying again.",
            parse_mode="HTML",
        )
        return False
    return True


async def _download_file(update: Update, context: ContextTypes.DEFAULT_TYPE, ext: str) -> str | None:
    """Download the document attached to the message. Returns local file path or None."""
    message = update.effective_message
    doc = message.document

    if not doc:
        await message.reply_text("❌ Please send a file (as a document, not compressed).")
        return None

    # Validate size
    is_valid, err = validate_file_size(doc.file_size)
    if not is_valid:
        await message.reply_text(err)
        return None

    # Download
    local_path = str(get_temp_path(ext))
    tg_file = await doc.get_file()
    await tg_file.download_to_drive(local_path)
    return local_path


async def _send_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_path: str,
    original_name: str,
    conversion_type: str,
    status_message,
) -> None:
    """Send the converted file back to the user and clean up."""
    output_name = auto_rename(original_name, conversion_type)

    # Edit the status message to show success
    try:
        await status_message.edit_text("✅ <b>Conversion successful!</b>", parse_mode="HTML")
    except Exception:
        pass

    # Send the file
    with open(file_path, "rb") as f:
        await update.effective_message.reply_document(
            document=f,
            filename=output_name,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")]]
            ),
        )

    # Cleanup
    cleanup_files(file_path)


# ═══════════════════════════════════════════════════════════════════════════
# Prompt handlers — triggered by inline keyboard selections
# ═══════════════════════════════════════════════════════════════════════════

async def prompt_pdf_to_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to upload a PDF for PDF → Word conversion."""
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "pdf_to_word"
    await query.edit_message_text(
        "📄 <b>PDF → Word</b>\n\nSend me a PDF file to convert.",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def prompt_word_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to upload a DOCX for Word → PDF conversion."""
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "word_to_pdf"
    await query.edit_message_text(
        "📝 <b>Word → PDF</b>\n\nSend me a Word (.docx) file to convert.",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def prompt_img_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to upload an image for Image → PDF conversion."""
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "img_to_pdf"
    await query.edit_message_text(
        "🖼 <b>Image → PDF</b>\n\nSend me an image (JPG, PNG, or WEBP) to convert.",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def prompt_merge_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to upload images for merging into a PDF."""
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "merge_images"
    context.user_data["merge_files"] = []
    await query.edit_message_text(
        "🗂 <b>Merge Images</b>\n\n"
        "Send me images one by one.\n"
        "When done, tap <b>✅ Done — Merge Now</b>.",
        parse_mode="HTML",
        reply_markup=DONE_KEYBOARD,
    )


async def prompt_compress_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to upload a PDF for compression."""
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "compress_pdf"
    await query.edit_message_text(
        "📦 <b>Compress PDF</b>\n\nSend me a PDF file to compress.",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def prompt_split_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to upload a PDF for splitting."""
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "split_pdf"
    await query.edit_message_text(
        "✂️ <b>Split PDF</b>\n\nSend me a PDF to split into individual pages.",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def prompt_extract_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to upload a PDF to extract images from."""
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "extract_images"
    await query.edit_message_text(
        "🖼 <b>Extract Images</b>\n\nSend me a PDF to extract images from.",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def prompt_pdf_to_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to upload a PDF to convert to images."""
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting"] = "pdf_to_images"
    await query.edit_message_text(
        "📸 <b>PDF → Images</b>\n\nSend me a PDF to convert each page to a PNG image.",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


# ═══════════════════════════════════════════════════════════════════════════
# File receive handler — processes uploads based on awaiting state
# ═══════════════════════════════════════════════════════════════════════════

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Central handler for all document uploads.
    Routes to the correct conversion based on context.user_data['awaiting'].
    """
    awaiting = context.user_data.get("awaiting")

    if not awaiting:
        # Auto-detect: suggest conversion based on file type
        await _auto_detect(update, context)
        return

    user_id = update.effective_user.id

    # Rate limit check
    if not await _check_rate_limit(update, user_id):
        return

    # Dispatch to the correct handler
    dispatch = {
        "pdf_to_word": _handle_pdf_to_word,
        "word_to_pdf": _handle_word_to_pdf,
        "img_to_pdf": _handle_img_to_pdf,
        "merge_images": _handle_merge_image_collect,
        "compress_pdf": _handle_compress_pdf,
        "split_pdf": _handle_split_pdf,
        "extract_images": _handle_extract_images,
        "pdf_to_images": _handle_pdf_to_images,
    }

    handler = dispatch.get(awaiting)
    if handler:
        await handler(update, context)
    else:
        await update.effective_message.reply_text(
            "❌ Unexpected state. Please use /start to begin again."
        )
        context.user_data.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Auto-detect file type
# ═══════════════════════════════════════════════════════════════════════════

async def _auto_detect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Suggest conversion options based on the uploaded file's MIME type."""
    doc = update.effective_message.document
    if not doc:
        await update.effective_message.reply_text(
            "Please select a tool from the menu first, or send a file and I'll suggest options.",
            parse_mode="HTML",
        )
        return

    mime = doc.mime_type or ""
    buttons = []

    if mime == "application/pdf":
        buttons = [
            [InlineKeyboardButton("📄 PDF → Word", callback_data="pdf_to_word")],
            [InlineKeyboardButton("📦 Compress PDF", callback_data="compress_pdf")],
            [InlineKeyboardButton("✂️ Split PDF", callback_data="split_pdf")],
            [InlineKeyboardButton("🖼 Extract Images", callback_data="extract_images")],
            [InlineKeyboardButton("📸 PDF → Images", callback_data="pdf_to_images")],
        ]
    elif mime in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        buttons = [
            [InlineKeyboardButton("📝 Word → PDF", callback_data="word_to_pdf")],
        ]
    elif mime.startswith("image/"):
        buttons = [
            [InlineKeyboardButton("🖼 Image → PDF", callback_data="img_to_pdf")],
            [InlineKeyboardButton("🗂 Merge Images", callback_data="merge_images")],
        ]

    if buttons:
        await update.effective_message.reply_text(
            "🤖 <b>I detected your file!</b>\nWhat would you like to do?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        await update.effective_message.reply_text(
            "❌ Unsupported file type. Please send a PDF, DOCX, or image file.",
            parse_mode="HTML",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Individual conversion handlers
# ═══════════════════════════════════════════════════════════════════════════

async def _handle_pdf_to_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.effective_message.document
    is_valid, err = validate_file_type(doc.mime_type, "pdf")
    if not is_valid:
        await update.effective_message.reply_text(err)
        return

    status = await update.effective_message.reply_text("⏳ <b>Processing...</b>", parse_mode="HTML")
    local_path = await _download_file(update, context, ".pdf")
    if not local_path:
        return

    try:
        user_id = update.effective_user.id

        async def do_convert():
            return await pdf_to_docx(local_path)

        future = await queue_manager.submit(user_id, do_convert())
        result_path = await future
        if result_path:
            await _send_result(update, context, result_path, doc.file_name, "pdf_to_docx", status)
        else:
            await status.edit_text("❌ Conversion was cancelled.", parse_mode="HTML")
    except Exception as exc:
        logger.error("PDF → Word failed: %s", exc, exc_info=True)
        await status.edit_text("❌ <b>Conversion failed</b>. Please try again.", parse_mode="HTML")
    finally:
        cleanup_files(local_path)
        context.user_data.pop("awaiting", None)


async def _handle_word_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.effective_message.document
    is_valid, err = validate_file_type(doc.mime_type, "docx")
    if not is_valid:
        await update.effective_message.reply_text(err)
        return

    status = await update.effective_message.reply_text("⏳ <b>Processing...</b>", parse_mode="HTML")
    local_path = await _download_file(update, context, ".docx")
    if not local_path:
        return

    try:
        user_id = update.effective_user.id

        async def do_convert():
            return await docx_to_pdf(local_path)

        future = await queue_manager.submit(user_id, do_convert())
        result_path = await future
        if result_path:
            await _send_result(update, context, result_path, doc.file_name, "docx_to_pdf", status)
        else:
            await status.edit_text("❌ Conversion was cancelled.", parse_mode="HTML")
    except Exception as exc:
        logger.error("Word → PDF failed: %s", exc, exc_info=True)
        await status.edit_text("❌ <b>Conversion failed</b>. Please try again.", parse_mode="HTML")
    finally:
        cleanup_files(local_path)
        context.user_data.pop("awaiting", None)


async def _handle_img_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.effective_message.document
    # Also accept photos sent as photos (not documents)
    photo = update.effective_message.photo
    is_image_doc = doc and doc.mime_type and doc.mime_type.startswith("image/")

    if not is_image_doc and not photo:
        await update.effective_message.reply_text(
            "❌ Please send an image file (JPG, PNG, or WEBP).",
            parse_mode="HTML",
        )
        return

    status = await update.effective_message.reply_text("⏳ <b>Processing...</b>", parse_mode="HTML")

    try:
        if is_image_doc:
            local_path = await _download_file(update, context, ".img")
        else:
            # Get highest-res photo
            photo_file = await photo[-1].get_file()
            local_path = str(get_temp_path(".jpg"))
            await photo_file.download_to_drive(local_path)

        if not local_path:
            return

        user_id = update.effective_user.id

        async def do_convert():
            return await image_to_pdf(local_path)

        future = await queue_manager.submit(user_id, do_convert())
        result_path = await future
        original_name = doc.file_name if doc else "photo.jpg"
        if result_path:
            await _send_result(update, context, result_path, original_name, "img_to_pdf", status)
        else:
            await status.edit_text("❌ Conversion was cancelled.", parse_mode="HTML")
    except Exception as exc:
        logger.error("Image → PDF failed: %s", exc, exc_info=True)
        await status.edit_text("❌ <b>Conversion failed</b>. Please try again.", parse_mode="HTML")
    finally:
        cleanup_files(local_path)
        context.user_data.pop("awaiting", None)


async def _handle_merge_image_collect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Collect images for merge — add to list, don't convert yet."""
    doc = update.effective_message.document
    photo = update.effective_message.photo
    is_image_doc = doc and doc.mime_type and doc.mime_type.startswith("image/")

    if not is_image_doc and not photo:
        await update.effective_message.reply_text(
            "❌ Please send an image file. When done, tap <b>✅ Done — Merge Now</b>.",
            parse_mode="HTML",
        )
        return

    try:
        if is_image_doc:
            local_path = await _download_file(update, context, ".img")
        else:
            photo_file = await photo[-1].get_file()
            local_path = str(get_temp_path(".jpg"))
            await photo_file.download_to_drive(local_path)

        if local_path:
            merge_files = context.user_data.setdefault("merge_files", [])
            merge_files.append(local_path)
            count = len(merge_files)
            await update.effective_message.reply_text(
                f"✅ Image {count} added. Send more or tap <b>Done</b>.",
                parse_mode="HTML",
                reply_markup=DONE_KEYBOARD,
            )
    except Exception as exc:
        logger.error("Merge image collect failed: %s", exc, exc_info=True)
        await update.effective_message.reply_text("❌ Failed to process image.", parse_mode="HTML")


async def handle_merge_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered when user taps 'Done — Merge Now'. Merge all collected images."""
    query = update.callback_query
    await query.answer()

    merge_files: list[str] = context.user_data.get("merge_files", [])
    if len(merge_files) < 2:
        await query.edit_message_text(
            "❌ Please send at least 2 images before merging.",
            parse_mode="HTML",
            reply_markup=DONE_KEYBOARD,
        )
        return

    user_id = update.effective_user.id
    if not rate_limiter.is_allowed(user_id):
        await query.edit_message_text(
            "⚠️ Rate limit exceeded. Please wait a minute.",
            parse_mode="HTML",
        )
        return

    status = await query.edit_message_text("⏳ <b>Merging images...</b>", parse_mode="HTML")

    try:
        async def do_merge():
            return await merge_images_to_pdf(merge_files)

        future = await queue_manager.submit(user_id, do_merge())
        result_path = await future

        if result_path:
            try:
                await status.edit_text("✅ <b>Merge successful!</b>", parse_mode="HTML")
            except Exception:
                pass

            output_name = f"merged_{len(merge_files)}_images.pdf"
            with open(result_path, "rb") as f:
                await query.message.reply_document(
                    document=f,
                    filename=output_name,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")]]
                    ),
                )
            cleanup_files(result_path)
    except Exception as exc:
        logger.error("Merge failed: %s", exc, exc_info=True)
        try:
            await status.edit_text("❌ <b>Merge failed</b>. Please try again.", parse_mode="HTML")
        except Exception:
            pass
    finally:
        # Cleanup all collected images
        cleanup_files(*merge_files)
        context.user_data.pop("merge_files", None)
        context.user_data.pop("awaiting", None)


async def _handle_compress_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.effective_message.document
    is_valid, err = validate_file_type(doc.mime_type, "pdf")
    if not is_valid:
        await update.effective_message.reply_text(err)
        return

    status = await update.effective_message.reply_text("⏳ <b>Compressing...</b>", parse_mode="HTML")
    local_path = await _download_file(update, context, ".pdf")
    if not local_path:
        return

    try:
        user_id = update.effective_user.id

        async def do_convert():
            return await compress_pdf(local_path)

        future = await queue_manager.submit(user_id, do_convert())
        result_path = await future

        if result_path:
            # Show compression stats
            original_size = Path(local_path).stat().st_size
            compressed_size = Path(result_path).stat().st_size
            reduction = ((original_size - compressed_size) / original_size) * 100
            reduction = max(0, reduction)

            try:
                await status.edit_text(
                    f"✅ <b>Compression successful!</b>\n"
                    f"📉 Reduced by {reduction:.1f}%",
                    parse_mode="HTML",
                )
            except Exception:
                pass

            output_name = auto_rename(doc.file_name, "compress_pdf")
            with open(result_path, "rb") as f:
                await update.effective_message.reply_document(
                    document=f,
                    filename=output_name,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")]]
                    ),
                )
            cleanup_files(result_path)
        else:
            await status.edit_text("❌ Compression was cancelled.", parse_mode="HTML")
    except Exception as exc:
        logger.error("Compress PDF failed: %s", exc, exc_info=True)
        await status.edit_text("❌ <b>Compression failed</b>. Please try again.", parse_mode="HTML")
    finally:
        cleanup_files(local_path)
        context.user_data.pop("awaiting", None)


async def _handle_split_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.effective_message.document
    is_valid, err = validate_file_type(doc.mime_type, "pdf")
    if not is_valid:
        await update.effective_message.reply_text(err)
        return

    status = await update.effective_message.reply_text("⏳ <b>Splitting...</b>", parse_mode="HTML")
    local_path = await _download_file(update, context, ".pdf")
    if not local_path:
        return

    try:
        user_id = update.effective_user.id

        async def do_convert():
            return await split_pdf(local_path)

        future = await queue_manager.submit(user_id, do_convert())
        result_path = await future
        if result_path:
            await _send_result(update, context, result_path, doc.file_name, "split_pdf", status)
        else:
            await status.edit_text("❌ Split was cancelled.", parse_mode="HTML")
    except Exception as exc:
        logger.error("Split PDF failed: %s", exc, exc_info=True)
        await status.edit_text("❌ <b>Split failed</b>. Please try again.", parse_mode="HTML")
    finally:
        cleanup_files(local_path)
        context.user_data.pop("awaiting", None)


async def _handle_extract_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.effective_message.document
    is_valid, err = validate_file_type(doc.mime_type, "pdf")
    if not is_valid:
        await update.effective_message.reply_text(err)
        return

    status = await update.effective_message.reply_text("⏳ <b>Extracting images...</b>", parse_mode="HTML")
    local_path = await _download_file(update, context, ".pdf")
    if not local_path:
        return

    try:
        user_id = update.effective_user.id

        async def do_convert():
            return await extract_images_from_pdf(local_path)

        future = await queue_manager.submit(user_id, do_convert())
        result_path = await future
        if result_path:
            await _send_result(update, context, result_path, doc.file_name, "extract_images", status)
        else:
            await status.edit_text("❌ Extraction was cancelled.", parse_mode="HTML")
    except ValueError as ve:
        await status.edit_text(f"❌ {ve}", parse_mode=None)
    except Exception as exc:
        logger.error("Extract images failed: %s", exc, exc_info=True)
        await status.edit_text("❌ <b>Extraction failed</b>. Please try again.", parse_mode="HTML")
    finally:
        cleanup_files(local_path)
        context.user_data.pop("awaiting", None)


async def _handle_pdf_to_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.effective_message.document
    is_valid, err = validate_file_type(doc.mime_type, "pdf")
    if not is_valid:
        await update.effective_message.reply_text(err)
        return

    status = await update.effective_message.reply_text("⏳ <b>Converting to images...</b>", parse_mode="HTML")
    local_path = await _download_file(update, context, ".pdf")
    if not local_path:
        return

    try:
        user_id = update.effective_user.id

        async def do_convert():
            return await pdf_to_images(local_path)

        future = await queue_manager.submit(user_id, do_convert())
        result_path = await future
        if result_path:
            await _send_result(update, context, result_path, doc.file_name, "pdf_to_images", status)
        else:
            await status.edit_text("❌ Conversion was cancelled.", parse_mode="HTML")
    except Exception as exc:
        logger.error("PDF → Images failed: %s", exc, exc_info=True)
        await status.edit_text("❌ <b>Conversion failed</b>. Please try again.", parse_mode="HTML")
    finally:
        cleanup_files(local_path)
        context.user_data.pop("awaiting", None)


# ═══════════════════════════════════════════════════════════════════════════
# Cancel handler
# ═══════════════════════════════════════════════════════════════════════════

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel the current operation and return to main menu."""
    query = update.callback_query
    await query.answer("Cancelled")

    user_id = update.effective_user.id
    queue_manager.cancel(user_id)

    # Cleanup any merge files
    merge_files = context.user_data.get("merge_files", [])
    if merge_files:
        cleanup_files(*merge_files)

    context.user_data.clear()

    await query.edit_message_text(
        "❌ <b>Operation cancelled.</b>\n\nChoose a tool to get started:",
        parse_mode="HTML",
        reply_markup=MAIN_MENU_KEYBOARD,
    )
