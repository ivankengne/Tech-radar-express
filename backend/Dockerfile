# ===================================
# Multi-stage Docker build pour Tech Radar Express Backend
# Optimisé pour la production avec sécurité renforcée
# ===================================

# ===== BUILD STAGE =====
FROM python:3.11-slim as builder

# Variables d'environnement pour l'optimisation
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installation des outils de build
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie des requirements et installation des dépendances
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ===== PRODUCTION STAGE =====
FROM python:3.11-slim as production

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH=/root/.local/bin:$PATH

# Installation des dépendances runtime seulement
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Création de l'utilisateur non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copie des dépendances Python depuis le build stage
COPY --from=builder /root/.local /root/.local

# Création des répertoires
WORKDIR /app
RUN mkdir -p /app/logs /app/uploads && \
    chown -R appuser:appuser /app

# Copie du code source
COPY --chown=appuser:appuser . .

# Changement vers l'utilisateur non-root
USER appuser

# Port d'exposition
EXPOSE 8000

# Commande de health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande par défaut
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"] 