FROM python:3.12-slim

# poppler-utils: pdf2image shells out to pdftoppm/pdfinfo for PDF -> image rendering.
# libreoffice-writer: DOCX -> PDF conversion (soffice --headless), before the same
# PDF -> image path. The -writer package alone (not the full libreoffice suite)
# pulls in libreoffice-core, which owns the soffice binary - no Calc/Impress needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
        libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "app.main:app"]
