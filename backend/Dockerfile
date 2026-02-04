FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# Application code
COPY src/ ./src/
COPY allowlist_sources.yaml .

# Set PYTHONPATH so 'from app.xxx' works
ENV PYTHONPATH=/app/src

# Create non-root user
RUN useradd -m scripe && chown -R scripe:scripe /app
USER scripe

EXPOSE 8010

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8010"]
