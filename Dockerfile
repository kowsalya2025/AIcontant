# ─────────────────────────────────────────────
#  Stage 1: Builder — installs Python deps
# ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps for PyTorch, FAISS, psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────
#  Stage 2: Runtime image
# ─────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project source
COPY . .

# Create directories needed at runtime
RUN mkdir -p /app/faiss_index /app/knowledge_base /app/media /app/staticfiles

# Expose Django dev server port
EXPOSE 8000

# Default: run Django dev server
# In production, swap for gunicorn
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
