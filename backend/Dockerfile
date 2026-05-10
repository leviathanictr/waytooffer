FROM python:3.11-bookworm

WORKDIR /app

# WeasyPrint native deps (Pango/Cairo/GDK) — bookworm has these in default repos
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist SQLite DB in /data volume
RUN mkdir -p /data
ENV DATABASE_URL=sqlite:////data/resume_builder.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
