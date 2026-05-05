import os
import io
import time
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename
import PyPDF2
from PIL import Image, ImageDraw, ImageFont

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from pdf2docx import Converter
except ImportError:
    Converter = None

try:
    from docx2pdf import convert as docx_convert
except ImportError:
    docx_convert = None

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER   = BASE_DIR / "uploads"
DOWNLOAD_FOLDER = BASE_DIR / "downloads"
TEMPLATE_FOLDER = BASE_DIR / "templates"
STATIC_FOLDER   = BASE_DIR / "static"

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_FOLDER),
    static_folder=str(STATIC_FOLDER),
)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["DOWNLOAD_FOLDER"] = str(DOWNLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB

UPLOAD_FOLDER.mkdir(exist_ok=True)
DOWNLOAD_FOLDER.mkdir(exist_ok=True)


def remove_file(path):
    try:
        path = Path(path)
        if path.exists():
            path.unlink()
    except Exception as e:
        print(f"Could not delete {path}: {e}")


def unique_name(filename):
    safe = secure_filename(filename)
    return f"{int(time.time())}_{safe}"


def is_pdf(filename):
    return filename.lower().endswith(".pdf")


@app.route("/")
def index():
    return render_template("index.html")


# ─── UPLOAD ──────────────────────────────────────────────────────────────────

@app.route("/upload", methods=["POST"])
def upload():
    if "files[]" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
    files = request.files.getlist("files[]")
    saved_files = []
    for file in files:
        if not file or file.filename == "":
            continue
        filename = unique_name(file.filename)
        file.save(UPLOAD_FOLDER / filename)
        saved_files.append(filename)
    if not saved_files:
        return jsonify({"error": "No valid files selected"}), 400
    return jsonify({"success": True, "files": saved_files})


# ─── COMPRESS ────────────────────────────────────────────────────────────────

@app.route("/compress", methods=["POST"])
def compress_pdf():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    target_size_mb = data.get("target_size")

    if not filename:
        return jsonify({"error": "Filename missing"}), 400
    if not is_pdf(filename):
        return jsonify({"error": "Compress PDF accepts only PDF files"}), 400

    input_path = UPLOAD_FOLDER / filename
    if not input_path.exists():
        return jsonify({"error": "Uploaded file not found"}), 404

    output_filename = f"compressed_{filename}"
    output_path = DOWNLOAD_FOLDER / output_filename

    try:
        target_size_mb = float(target_size_mb) if target_size_mb else None
    except ValueError:
        target_size_mb = None

    try:
        if fitz:
            doc = fitz.open(input_path)
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            if target_size_mb:
                current_size_mb = output_path.stat().st_size / (1024 * 1024)
                if current_size_mb > target_size_mb:
                    ratio = max(target_size_mb / current_size_mb, 0.05)
                    zoom = max(min((ratio ** 0.5) * 0.9, 1.0), 0.25)
                    quality = 60 if ratio < 0.7 else 75
                    compressed_doc = fitz.open()
                    matrix = fitz.Matrix(zoom, zoom)
                    for page in doc:
                        pix = page.get_pixmap(matrix=matrix, alpha=False)
                        img_pdf = fitz.open()
                        img_page = img_pdf.new_page(width=page.rect.width, height=page.rect.height)
                        img_bytes = pix.tobytes("jpeg", jpg_quality=quality)
                        img_page.insert_image(page.rect, stream=img_bytes)
                        compressed_doc.insert_pdf(img_pdf)
                        img_pdf.close()
                    temp_output = DOWNLOAD_FOLDER / f"temp_{output_filename}"
                    compressed_doc.save(temp_output, garbage=4, deflate=True)
                    compressed_doc.close()
                    remove_file(output_path)
                    temp_output.rename(output_path)
            doc.close()
        else:
            reader = PyPDF2.PdfReader(str(input_path))
            writer = PyPDF2.PdfWriter()
            for page in reader.pages:
                try:
                    page.compress_content_streams()
                except Exception:
                    pass
                writer.add_page(page)
            writer.add_metadata({})
            with open(output_path, "wb") as f:
                writer.write(f)

        original_size = input_path.stat().st_size if input_path.exists() else 0
        remove_file(input_path)
        new_size = output_path.stat().st_size

        return jsonify({
            "success": True,
            "filename": output_filename,
            "download_url": f"/download/{output_filename}",
            "original_size": original_size,
            "new_size": new_size
        })
    except Exception as e:
        return jsonify({"error": f"Compression failed: {str(e)}"}), 500


# ─── MERGE ───────────────────────────────────────────────────────────────────

@app.route("/merge", methods=["POST"])
def merge_pdf():
    data = request.get_json(silent=True) or {}
    filenames = data.get("filenames", [])
    if len(filenames) < 2:
        return jsonify({"error": "Please select at least 2 PDF files to merge"}), 400
    for filename in filenames:
        if not is_pdf(filename):
            return jsonify({"error": "Merge PDF accepts only PDF files"}), 400

    output_filename = f"merged_{int(time.time())}.pdf"
    output_path = DOWNLOAD_FOLDER / output_filename
    try:
        merger = PyPDF2.PdfMerger()
        for filename in filenames:
            file_path = UPLOAD_FOLDER / filename
            if not file_path.exists():
                merger.close()
                return jsonify({"error": f"File not found: {filename}"}), 404
            merger.append(str(file_path))
        merger.write(str(output_path))
        merger.close()
        for filename in filenames:
            remove_file(UPLOAD_FOLDER / filename)
        return jsonify({"success": True, "filename": output_filename, "download_url": f"/download/{output_filename}"})
    except Exception as e:
        return jsonify({"error": f"Merge failed: {str(e)}"}), 500


# ─── SPLIT ───────────────────────────────────────────────────────────────────

@app.route("/split", methods=["POST"])
def split_pdf():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    page_ranges = data.get("page_ranges", "")  # e.g. "1-3,5,7-9"

    if not filename:
        return jsonify({"error": "Filename missing"}), 400
    if not is_pdf(filename):
        return jsonify({"error": "Split PDF accepts only PDF files"}), 400

    input_path = UPLOAD_FOLDER / filename
    if not input_path.exists():
        return jsonify({"error": "Uploaded file not found"}), 404

    base_name = Path(filename).stem
    output_zipname = f"{base_name}_split.zip"
    output_zip_path = DOWNLOAD_FOLDER / output_zipname

    try:
        reader = PyPDF2.PdfReader(str(input_path))
        total_pages = len(reader.pages)

        # Parse page ranges
        pages_to_extract = []
        if page_ranges.strip():
            for part in page_ranges.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = part.split("-")
                    start, end = int(start.strip()) - 1, int(end.strip()) - 1
                    pages_to_extract.extend(range(max(0, start), min(total_pages, end + 1)))
                else:
                    p = int(part) - 1
                    if 0 <= p < total_pages:
                        pages_to_extract.append(p)
        else:
            pages_to_extract = list(range(total_pages))

        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for page_number in pages_to_extract:
                writer = PyPDF2.PdfWriter()
                writer.add_page(reader.pages[page_number])
                page_filename = f"page_{page_number + 1}.pdf"
                page_path = DOWNLOAD_FOLDER / page_filename
                with open(page_path, "wb") as page_file:
                    writer.write(page_file)
                zipf.write(page_path, page_filename)
                remove_file(page_path)

        remove_file(input_path)
        return jsonify({"success": True, "filename": output_zipname, "download_url": f"/download/{output_zipname}"})
    except Exception as e:
        return jsonify({"error": f"Split failed: {str(e)}"}), 500


# ─── ROTATE ──────────────────────────────────────────────────────────────────

@app.route("/rotate", methods=["POST"])
def rotate_pdf():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    angle = data.get("angle", 90)

    if not filename:
        return jsonify({"error": "Filename missing"}), 400
    if not is_pdf(filename):
        return jsonify({"error": "Rotate PDF accepts only PDF files"}), 400

    input_path = UPLOAD_FOLDER / filename
    if not input_path.exists():
        return jsonify({"error": "Uploaded file not found"}), 404

    output_filename = f"rotated_{filename}"
    output_path = DOWNLOAD_FOLDER / output_filename

    try:
        reader = PyPDF2.PdfReader(str(input_path))
        writer = PyPDF2.PdfWriter()
        for page in reader.pages:
            page.rotate(int(angle))
            writer.add_page(page)
        with open(output_path, "wb") as f:
            writer.write(f)
        remove_file(input_path)
        return jsonify({"success": True, "filename": output_filename, "download_url": f"/download/{output_filename}"})
    except Exception as e:
        return jsonify({"error": f"Rotate failed: {str(e)}"}), 500


# ─── WATERMARK ───────────────────────────────────────────────────────────────

@app.route("/watermark", methods=["POST"])
def watermark_pdf():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    text = data.get("text", "CONFIDENTIAL")
    opacity = float(data.get("opacity", 0.3))
    color = data.get("color", "#FF0000")

    if not filename:
        return jsonify({"error": "Filename missing"}), 400
    if not is_pdf(filename):
        return jsonify({"error": "Watermark PDF accepts only PDF files"}), 400

    input_path = UPLOAD_FOLDER / filename
    if not input_path.exists():
        return jsonify({"error": "Uploaded file not found"}), 404

    output_filename = f"watermarked_{filename}"
    output_path = DOWNLOAD_FOLDER / output_filename

    try:
        if fitz:
            import math
            doc = fitz.open(str(input_path))

            # Parse hex color
            r = int(color[1:3], 16) / 255.0
            g = int(color[3:5], 16) / 255.0
            b = int(color[5:7], 16) / 255.0

            for page in doc:
                rect = page.rect
                fontsize = min(rect.width, rect.height) * 0.08
                pivot = fitz.Point(rect.width / 2, rect.height / 2)
                # 45-degree rotation matrix (fitz insert_text only allows 0/90/180/270
                # so we use the morph parameter for arbitrary angle)
                morph_mat = fitz.Matrix(45)
                page.insert_text(
                    fitz.Point(rect.width * 0.05, rect.height * 0.55),
                    text,
                    fontsize=fontsize,
                    color=(r, g, b),
                    rotate=0,
                    fill_opacity=opacity,
                    morph=(pivot, morph_mat),
                    fontname="helv"
                )

            doc.save(str(output_path), garbage=4, deflate=True)
            doc.close()
        else:
            # Fallback: plain copy (no fitz = no diagonal watermark support)
            reader = PyPDF2.PdfReader(str(input_path))
            writer = PyPDF2.PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(output_path, "wb") as f:
                writer.write(f)

        remove_file(input_path)
        return jsonify({"success": True, "filename": output_filename, "download_url": f"/download/{output_filename}"})
    except Exception as e:
        return jsonify({"error": f"Watermark failed: {str(e)}"}), 500


# ─── PROTECT PDF ─────────────────────────────────────────────────────────────

@app.route("/protect", methods=["POST"])
def protect_pdf():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    password = data.get("password", "")

    if not filename:
        return jsonify({"error": "Filename missing"}), 400
    if not password:
        return jsonify({"error": "Password is required"}), 400
    if not is_pdf(filename):
        return jsonify({"error": "Protect PDF accepts only PDF files"}), 400

    input_path = UPLOAD_FOLDER / filename
    if not input_path.exists():
        return jsonify({"error": "Uploaded file not found"}), 404

    output_filename = f"protected_{filename}"
    output_path = DOWNLOAD_FOLDER / output_filename

    try:
        reader = PyPDF2.PdfReader(str(input_path))
        writer = PyPDF2.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)
        with open(output_path, "wb") as f:
            writer.write(f)
        remove_file(input_path)
        return jsonify({"success": True, "filename": output_filename, "download_url": f"/download/{output_filename}"})
    except Exception as e:
        return jsonify({"error": f"Protect failed: {str(e)}"}), 500


# ─── UNLOCK PDF ──────────────────────────────────────────────────────────────

@app.route("/unlock", methods=["POST"])
def unlock_pdf():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    password = data.get("password", "")

    if not filename:
        return jsonify({"error": "Filename missing"}), 400
    if not is_pdf(filename):
        return jsonify({"error": "Unlock PDF accepts only PDF files"}), 400

    input_path = UPLOAD_FOLDER / filename
    if not input_path.exists():
        return jsonify({"error": "Uploaded file not found"}), 404

    output_filename = f"unlocked_{filename}"
    output_path = DOWNLOAD_FOLDER / output_filename

    try:
        reader = PyPDF2.PdfReader(str(input_path))
        if reader.is_encrypted:
            if not reader.decrypt(password):
                return jsonify({"error": "Incorrect password"}), 400

        writer = PyPDF2.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        with open(output_path, "wb") as f:
            writer.write(f)
        remove_file(input_path)
        return jsonify({"success": True, "filename": output_filename, "download_url": f"/download/{output_filename}"})
    except Exception as e:
        return jsonify({"error": f"Unlock failed: {str(e)}"}), 500


# ─── EXTRACT TEXT ─────────────────────────────────────────────────────────────

@app.route("/extract-text", methods=["POST"])
def extract_text():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")

    if not filename:
        return jsonify({"error": "Filename missing"}), 400
    if not is_pdf(filename):
        return jsonify({"error": "Extract Text accepts only PDF files"}), 400

    input_path = UPLOAD_FOLDER / filename
    if not input_path.exists():
        return jsonify({"error": "Uploaded file not found"}), 404

    output_filename = f"{Path(filename).stem}_text.txt"
    output_path = DOWNLOAD_FOLDER / output_filename

    try:
        text_content = []
        if fitz:
            doc = fitz.open(str(input_path))
            for i, page in enumerate(doc):
                text_content.append(f"--- Page {i+1} ---\n{page.get_text()}")
            doc.close()
        else:
            reader = PyPDF2.PdfReader(str(input_path))
            for i, page in enumerate(reader.pages):
                text_content.append(f"--- Page {i+1} ---\n{page.extract_text() or ''}")

        full_text = "\n\n".join(text_content)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        remove_file(input_path)
        return jsonify({"success": True, "filename": output_filename, "download_url": f"/download/{output_filename}"})
    except Exception as e:
        return jsonify({"error": f"Extract text failed: {str(e)}"}), 500


# ─── PDF INFO ─────────────────────────────────────────────────────────────────

@app.route("/pdf-info", methods=["POST"])
def pdf_info():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")

    if not filename:
        return jsonify({"error": "Filename missing"}), 400

    input_path = UPLOAD_FOLDER / filename
    if not input_path.exists():
        return jsonify({"error": "Uploaded file not found"}), 404

    try:
        reader = PyPDF2.PdfReader(str(input_path))
        meta = reader.metadata or {}
        info = {
            "page_count": len(reader.pages),
            "title": meta.get("/Title", "N/A"),
            "author": meta.get("/Author", "N/A"),
            "creator": meta.get("/Creator", "N/A"),
            "encrypted": reader.is_encrypted,
            "file_size_kb": round(input_path.stat().st_size / 1024, 2),
        }
        if fitz and not reader.is_encrypted:
            doc = fitz.open(str(input_path))
            page = doc[0]
            info["page_width_pt"] = round(page.rect.width, 1)
            info["page_height_pt"] = round(page.rect.height, 1)
            doc.close()
        remove_file(input_path)
        return jsonify({"success": True, "info": info})
    except Exception as e:
        return jsonify({"error": f"Could not read PDF info: {str(e)}"}), 500


# ─── CONVERSIONS ─────────────────────────────────────────────────────────────

@app.route("/convert/jpg-to-pdf", methods=["POST"])
def jpg_to_pdf():
    data = request.get_json(silent=True) or {}
    filenames = data.get("filenames", [])
    if not filenames:
        return jsonify({"error": "No image files selected"}), 400

    output_filename = f"images_{int(time.time())}.pdf"
    output_path = DOWNLOAD_FOLDER / output_filename
    try:
        images = []
        for filename in filenames:
            file_path = UPLOAD_FOLDER / filename
            img = Image.open(file_path).convert("RGB")
            images.append(img)
        first_image = images[0]
        other_images = images[1:]
        first_image.save(output_path, save_all=True, append_images=other_images)
        for filename in filenames:
            remove_file(UPLOAD_FOLDER / filename)
        return jsonify({"success": True, "filename": output_filename, "download_url": f"/download/{output_filename}"})
    except Exception as e:
        return jsonify({"error": f"JPG to PDF failed: {str(e)}"}), 500


@app.route("/convert/pdf-to-word", methods=["POST"])
def pdf_to_word():
    if Converter is None:
        return jsonify({"error": "pdf2docx is not installed"}), 500
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    input_path = UPLOAD_FOLDER / filename
    output_filename = f"{Path(filename).stem}.docx"
    output_path = DOWNLOAD_FOLDER / output_filename
    try:
        cv = Converter(str(input_path))
        cv.convert(str(output_path), start=0, end=None)
        cv.close()
        remove_file(input_path)
        return jsonify({"success": True, "filename": output_filename, "download_url": f"/download/{output_filename}"})
    except Exception as e:
        return jsonify({"error": f"PDF to Word failed: {str(e)}"}), 500


@app.route("/convert/word-to-pdf", methods=["POST"])
def word_to_pdf():
    if docx_convert is None:
        return jsonify({"error": "docx2pdf is not installed or not supported on this system"}), 500
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    input_path = UPLOAD_FOLDER / filename
    output_filename = f"{Path(filename).stem}.pdf"
    output_path = DOWNLOAD_FOLDER / output_filename
    try:
        docx_convert(str(input_path), str(output_path))
        remove_file(input_path)
        return jsonify({"success": True, "filename": output_filename, "download_url": f"/download/{output_filename}"})
    except Exception as e:
        return jsonify({"error": f"Word to PDF failed: {str(e)}"}), 500


@app.route("/convert/pdf-to-jpg", methods=["POST"])
def pdf_to_jpg():
    if fitz is None:
        return jsonify({"error": "PyMuPDF is not installed"}), 500
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    input_path = UPLOAD_FOLDER / filename
    output_zipname = f"{Path(filename).stem}_jpg.zip"
    output_zip_path = DOWNLOAD_FOLDER / output_zipname
    try:
        doc = fitz.open(input_path)
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for page_number in range(len(doc)):
                page = doc.load_page(page_number)
                pix = page.get_pixmap(alpha=False)
                image_name = f"page_{page_number + 1}.jpg"
                image_path = DOWNLOAD_FOLDER / image_name
                pix.save(image_path)
                zipf.write(image_path, image_name)
                remove_file(image_path)
        doc.close()
        remove_file(input_path)
        return jsonify({"success": True, "filename": output_zipname, "download_url": f"/download/{output_zipname}"})
    except Exception as e:
        return jsonify({"error": f"PDF to JPG failed: {str(e)}"}), 500


# ─── DOWNLOAD ────────────────────────────────────────────────────────────────

@app.route("/download/<filename>")
def download(filename):
    safe_filename = secure_filename(filename)
    file_path = DOWNLOAD_FOLDER / safe_filename
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    @after_this_request
    def cleanup(response):
        remove_file(file_path)
        return response

    return send_file(file_path, as_attachment=True, download_name=safe_filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
