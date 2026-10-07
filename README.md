# Quick PDF Converter

A fast, mobile-friendly web app for everyday PDF tasks, inspired by SmallPDF and iLovePDF. Built with Flask.

**Live demo:** _add your Render link here_

![Screenshot](screenshot.png)

## Features

- Compress, merge and split PDFs
- Rotate pages and add text watermarks
- Protect (add password) and unlock PDFs
- Extract text and view PDF info / health check
- Convert: PDF to Word, PDF to JPG, JPG/PNG to PDF
- Word to PDF (local use only, needs Microsoft Word on Windows/macOS)
- Responsive design that works on phones

## Tech stack

Python, Flask, PyPDF2, PyMuPDF, pdf2docx, Pillow, vanilla JavaScript, HTML/CSS. Deployed with Gunicorn on Render.

## Run locally

```bash
git clone https://github.com/abhijithm17/quick-pdf-converter.git
cd quick-pdf-converter

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Deploy on Render

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

Files are deleted from the server after processing.

## Project structure

```
app.py            Flask routes and PDF logic
templates/        HTML page
static/           CSS and JavaScript
requirements.txt  Dependencies
```

## Author

Abhijith M. [GitHub](https://github.com/abhijithm17) | [LinkedIn](https://linkedin.com/in/abhijith-m0505)
