FROM python:3.12-slim

WORKDIR /app

# build-essential: compila extensões C de algumas dependências Python
# libpq-dev: headers psycopg2 (necessário se algum driver Supabase os usar)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python primeiro para aproveitar cache de layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY . .

# Pasta para segredos montados em runtime (Google credentials, etc.)
RUN mkdir -p /app/secrets

EXPOSE 8000

# --workers 1: MemorySaver do LangGraph não é thread-safe com múltiplos workers
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
