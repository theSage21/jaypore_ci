FROM python:3.12-slim

WORKDIR /app

# Install build dependencies for common Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY manage.py .
COPY mysite/ mysite/
COPY core/ core/
COPY setup.cfg .

EXPOSE 8000

CMD ["gunicorn", "mysite.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
