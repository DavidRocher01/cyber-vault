# ── Stage 1: scanner-tools — Download binary security scanners ────────────────
# Uses a minimal Debian image; only curl is needed to fetch pre-built binaries.
FROM debian:bookworm-slim AS scanner-tools

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /tools

RUN GITLEAKS_VERSION=8.30.1 \
    && curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
       | tar -xz -C /tools gitleaks \
    # trivy
    && TRIVY_VERSION=0.69.3 \
    && curl -sSfL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
       | tar -xz -C /tools trivy \
    # trufflehog
    && TRUFFLEHOG_VERSION=3.88.1 \
    && curl -sSfL "https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_amd64.tar.gz" \
       | tar -xz -C /tools trufflehog \
    # grype
    && GRYPE_VERSION=0.90.0 \
    && curl -sSfL "https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}/grype_${GRYPE_VERSION}_linux_amd64.tar.gz" \
       | tar -xz -C /tools grype \
    # osv-scanner
    && OSV_VERSION=1.9.2 \
    && curl -sSfL "https://github.com/google/osv-scanner/releases/download/v${OSV_VERSION}/osv-scanner_linux_amd64" \
       -o /tools/osv-scanner && chmod +x /tools/osv-scanner \
    # hadolint
    && HADOLINT_VERSION=2.12.0 \
    && curl -sSfL "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-Linux-x86_64" \
       -o /tools/hadolint && chmod +x /tools/hadolint \
    # tfsec
    && TFSEC_VERSION=1.28.11 \
    && curl -sSfL "https://github.com/aquasecurity/tfsec/releases/download/v${TFSEC_VERSION}/tfsec-linux-amd64" \
       -o /tools/tfsec && chmod +x /tools/tfsec \
    # gosec
    && GOSEC_VERSION=2.22.4 \
    && curl -sSfL "https://github.com/securego/gosec/releases/download/v${GOSEC_VERSION}/gosec_${GOSEC_VERSION}_linux_amd64.tar.gz" \
       | tar -xz -C /tools gosec \
    # bearer
    && BEARER_VERSION=1.48.0 \
    && curl -sSfL "https://github.com/bearer/bearer/releases/download/v${BEARER_VERSION}/bearer_${BEARER_VERSION}_linux_amd64.tar.gz" \
       | tar -xz -C /tools bearer


# ── Stage 2: python-deps — Install Python packages into an isolated venv ──────
FROM python:3.12-slim AS python-deps

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY backend/requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt \
    && pip install --no-cache-dir --no-deps safety==2.3.5

COPY cyber-scanner/requirements.txt ./scanner-requirements.txt
RUN pip install --no-cache-dir -r scanner-requirements.txt


# ── Stage 3: final runtime image ──────────────────────────────────────────────
FROM python:3.12-slim AS final

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Apply OS security patches + minimal runtime system tools
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        curl wget git nodejs npm ca-certificates nmap \
    && npm install -g eslint@8 eslint-plugin-security@3 --silent \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Scanner binaries (from scanner-tools stage)
COPY --from=scanner-tools /tools/ /usr/local/bin/

# Python packages (from python-deps stage)
COPY --from=python-deps /venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

COPY cyber-scanner/ /cyber-scanner/
COPY backend/ .

RUN useradd -r -u 1001 -s /bin/false appuser \
    && chown -R appuser:root /app /cyber-scanner

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Les migrations NE sont PAS jouées au démarrage du conteneur : elles le sont par
# une tâche dédiée one-shot (prod: .github/workflows/deploy.yml ; staging:
# `docker compose exec backend alembic upgrade head`). Migrer ici relancerait
# `alembic upgrade head` à chaque démarrage de chaque tâche ECS -> race possible
# si le service scale (>1 réplica) avec une migration lourde (cf. docs/RELEASE_RUNBOOK.md).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --forwarded-allow-ips=${TRUSTED_PROXY_IPS:-127.0.0.1}"]
