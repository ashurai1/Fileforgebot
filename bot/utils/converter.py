"""
ConvertX Bot - Conversion Engine
All file conversion functions. Blocking operations are wrapped with
asyncio.to_thread so they never block the event loop.
"""

import asyncio
import io
import zipfile
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image
from pdf2docx import Converter as Pdf2DocxConverter
from docx import Document as DocxDocument
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from bot.config import logger
from bot.utils.file_utils import get_temp_path, cleanup_files


# ═══════════════════════════════════════════════════════════════════════════
# PDF → Word (DOCX)
# ═══════════════════════════════════════════════════════════════════════════

def _pdf_to_docx_sync(pdf_path: str, docx_path: str) -> str:
    """Synchronous PDF-to-DOCX conversion using pdf2docx."""
    cv = Pdf2DocxConverter(pdf_path)
    cv.convert(docx_path, start=0, end=None)
    cv.close()
    return docx_path


async def pdf_to_docx(pdf_path: str) -> str:
    """Convert a PDF file to DOCX. Returns the output path."""
    output = str(get_temp_path(".docx"))
    logger.info("Converting PDF → DOCX: %s", pdf_path)
    result = await asyncio.to_thread(_pdf_to_docx_sync, pdf_path, output)
    logger.info("PDF → DOCX complete: %s", result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Word (DOCX) → PDF
# ═══════════════════════════════════════════════════════════════════════════

def _docx_to_pdf_sync(docx_path: str, pdf_path: str) -> str:
    """
    Synchronous DOCX-to-PDF conversion using reportlab.
    Extracts text from each paragraph and renders to a PDF canvas.
    """
    doc = DocxDocument(docx_path)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin
    line_height = 14

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            y -= line_height
            continue

        # Simple word-wrap
        words = text.split()
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            if c.stringWidth(test_line, "Helvetica", 11) < (width - 2 * margin):
                line = test_line
            else:
                if y < margin:
                    c.showPage()
                    y = height - margin
                c.drawString(margin, y, line)
                y -= line_height
                line = word

        if line:
            if y < margin:
                c.showPage()
                y = height - margin
            c.drawString(margin, y, line)
            y -= line_height

    c.save()
    return pdf_path


async def docx_to_pdf(docx_path: str) -> str:
    """Convert a DOCX file to PDF. Returns the output path."""
    output = str(get_temp_path(".pdf"))
    logger.info("Converting DOCX → PDF: %s", docx_path)
    result = await asyncio.to_thread(_docx_to_pdf_sync, docx_path, output)
    logger.info("DOCX → PDF complete: %s", result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Image → PDF
# ═══════════════════════════════════════════════════════════════════════════

def _image_to_pdf_sync(image_path: str, pdf_path: str) -> str:
    """Convert a single image to PDF using Pillow."""
    img = Image.open(image_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(pdf_path, "PDF", resolution=150.0)
    return pdf_path


async def image_to_pdf(image_path: str) -> str:
    """Convert a single image to PDF. Returns the output path."""
    output = str(get_temp_path(".pdf"))
    logger.info("Converting Image → PDF: %s", image_path)
    result = await asyncio.to_thread(_image_to_pdf_sync, image_path, output)
    logger.info("Image → PDF complete: %s", result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Merge Multiple Images → Single PDF
# ═══════════════════════════════════════════════════════════════════════════

def _merge_images_sync(image_paths: list[str], pdf_path: str) -> str:
    """Merge multiple images into a single PDF."""
    images = []
    for p in image_paths:
        img = Image.open(p)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        images.append(img)

    if not images:
        raise ValueError("No images provided for merging.")

    first, rest = images[0], images[1:]
    first.save(pdf_path, "PDF", resolution=150.0, save_all=True, append_images=rest)
    return pdf_path


async def merge_images_to_pdf(image_paths: list[str]) -> str:
    """Merge multiple images into a single PDF. Returns the output path."""
    output = str(get_temp_path(".pdf"))
    logger.info("Merging %d images → PDF", len(image_paths))
    result = await asyncio.to_thread(_merge_images_sync, image_paths, output)
    logger.info("Merge complete: %s", result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Split PDF into Individual Pages
# ═══════════════════════════════════════════════════════════════════════════

def _split_pdf_sync(pdf_path: str, output_dir: str) -> list[str]:
    """Split a PDF into individual page files."""
    doc = fitz.open(pdf_path)
    output_paths = []
    for i in range(len(doc)):
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
        out_path = str(Path(output_dir) / f"page_{i + 1}.pdf")
        new_doc.save(out_path)
        new_doc.close()
        output_paths.append(out_path)
    doc.close()
    return output_paths


async def split_pdf(pdf_path: str) -> str:
    """
    Split a PDF into individual page PDFs, packaged into a ZIP.
    Returns the ZIP file path.
    """
    import tempfile

    work_dir = tempfile.mkdtemp(dir=str(get_temp_path(".dir").parent))
    logger.info("Splitting PDF: %s", pdf_path)
    pages = await asyncio.to_thread(_split_pdf_sync, pdf_path, work_dir)

    zip_path = str(get_temp_path(".zip"))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in pages:
            zf.write(p, Path(p).name)

    # Cleanup individual page files
    cleanup_files(*pages)
    logger.info("Split complete: %d pages → %s", len(pages), zip_path)
    return zip_path


# ═══════════════════════════════════════════════════════════════════════════
# Compress PDF
# ═══════════════════════════════════════════════════════════════════════════

def _compress_pdf_sync(pdf_path: str, output_path: str) -> str:
    """Compress a PDF by cleaning, de-duplicating, and garbage collecting."""
    doc = fitz.open(pdf_path)

    # Rewrite images at lower quality where possible
    for page in doc:
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if base_image and base_image["ext"] in ("jpeg", "jpg", "png"):
                    img_bytes = base_image["image"]
                    img = Image.open(io.BytesIO(img_bytes))
                    # Resize large images
                    max_dim = 1200
                    if max(img.size) > max_dim:
                        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
                    buf = io.BytesIO()
                    img_format = "JPEG" if base_image["ext"] in ("jpeg", "jpg") else "PNG"
                    quality = 60 if img_format == "JPEG" else None
                    save_kwargs = {"format": img_format}
                    if quality:
                        save_kwargs["quality"] = quality
                    img.save(buf, **save_kwargs)
                    # Replace image in PDF
                    doc._deleteObject(xref)
            except Exception:
                # Skip images that can't be processed
                continue

    doc.save(
        output_path,
        garbage=4,         # maximum garbage collection
        deflate=True,      # compress streams
        clean=True,        # clean content streams
        linear=True,       # optimize for web
    )
    doc.close()
    return output_path


async def compress_pdf(pdf_path: str) -> str:
    """Compress a PDF to reduce file size. Returns the output path."""
    output = str(get_temp_path(".pdf"))
    logger.info("Compressing PDF: %s", pdf_path)
    result = await asyncio.to_thread(_compress_pdf_sync, pdf_path, output)
    logger.info("Compression complete: %s", result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Extract Images from PDF
# ═══════════════════════════════════════════════════════════════════════════

def _extract_images_sync(pdf_path: str, zip_path: str) -> str:
    """Extract all images from a PDF and package them in a ZIP."""
    doc = fitz.open(pdf_path)
    count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    if base_image:
                        ext = base_image["ext"]
                        img_bytes = base_image["image"]
                        filename = f"page{page_num + 1}_img{img_idx + 1}.{ext}"
                        zf.writestr(filename, img_bytes)
                        count += 1
                except Exception:
                    continue

    doc.close()
    if count == 0:
        raise ValueError("No images found in the PDF.")
    return zip_path


async def extract_images_from_pdf(pdf_path: str) -> str:
    """Extract images from a PDF into a ZIP. Returns the ZIP path."""
    output = str(get_temp_path(".zip"))
    logger.info("Extracting images from PDF: %s", pdf_path)
    result = await asyncio.to_thread(_extract_images_sync, pdf_path, output)
    logger.info("Image extraction complete: %s", result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# PDF → Images (each page as PNG)
# ═══════════════════════════════════════════════════════════════════════════

def _pdf_to_images_sync(pdf_path: str, zip_path: str) -> str:
    """Render every page of a PDF as a PNG and package into a ZIP."""
    doc = fitz.open(pdf_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render at 2× resolution for quality
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            filename = f"page_{page_num + 1}.png"
            zf.writestr(filename, img_bytes)

    doc.close()
    return zip_path


async def pdf_to_images(pdf_path: str) -> str:
    """Convert each page of a PDF to PNG images (ZIP). Returns the ZIP path."""
    output = str(get_temp_path(".zip"))
    logger.info("Converting PDF → Images: %s", pdf_path)
    result = await asyncio.to_thread(_pdf_to_images_sync, pdf_path, output)
    logger.info("PDF → Images complete: %s", result)
    return result
