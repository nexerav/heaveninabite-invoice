FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY db_init.py .
COPY pdf_gen.py .
COPY templates/ templates/
COPY static/ static/

RUN mkdir -p /app/data /app/data/exports

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

EXPOSE 5004

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5004/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5004", "--workers", "1", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
