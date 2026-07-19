# ── Stage 1: scanner-tools — Download binary security scanners ────────────────
# Uses a minimal Debian image; only curl is needed to fetch pre-built binaries.
FROM debian:bookworm-slim AS scanner-tools

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /tools

# Binaires d'outils de scan épinglés + VÉRIFIÉS par SHA256 (supply-chain) :
# on télécharge dans un fichier, on contrôle l'empreinte, puis on extrait.
# Un binaire altéré en amont/en transit fait échouer le build (sha256sum -c).
# Empreintes issues des checksums officiels de chaque release (ou calculées sur
# l'artefact exact). À mettre à jour en même temps que la version.
RUN set -eux; \
    dl() { curl -sSfL --retry 3 "$1" -o "$2"; echo "$3  $2" | sha256sum -c -; }; \
    # gitleaks 8.30.1
    dl "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz" gitleaks.tgz \
       "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"; \
    tar -xzf gitleaks.tgz gitleaks; rm gitleaks.tgz; \
    # trivy 0.69.3
    dl "https://github.com/aquasecurity/trivy/releases/download/v0.69.3/trivy_0.69.3_Linux-64bit.tar.gz" trivy.tgz \
       "1816b632dfe529869c740c0913e36bd1629cb7688bd5634f4a858c1d57c88b75"; \
    tar -xzf trivy.tgz trivy; rm trivy.tgz; \
    # trufflehog 3.88.1
    dl "https://github.com/trufflesecurity/trufflehog/releases/download/v3.88.1/trufflehog_3.88.1_linux_amd64.tar.gz" th.tgz \
       "0de286551c75b2f890f2c577ca97d761510641ecf3cabfdcdf4897c2c9901794"; \
    tar -xzf th.tgz trufflehog; rm th.tgz; \
    # grype 0.90.0
    dl "https://github.com/anchore/grype/releases/download/v0.90.0/grype_0.90.0_linux_amd64.tar.gz" grype.tgz \
       "48430d83f6bd75066ba936fb9e98543194b092cf68dc971ae8ab68b7ff05f8d1"; \
    tar -xzf grype.tgz grype; rm grype.tgz; \
    # osv-scanner 1.9.2 (binaire brut)
    dl "https://github.com/google/osv-scanner/releases/download/v1.9.2/osv-scanner_linux_amd64" osv-scanner \
       "d6af4b67fa5de658598bd2d445efb99e90d1734b3146962418719c4350ecb74b"; \
    chmod +x osv-scanner; \
    # hadolint 2.12.0 (binaire brut)
    dl "https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64" hadolint \
       "56de6d5e5ec427e17b74fa48d51271c7fc0d61244bf5c90e828aab8362d55010"; \
    chmod +x hadolint; \
    # tfsec 1.28.11 (binaire brut)
    dl "https://github.com/aquasecurity/tfsec/releases/download/v1.28.11/tfsec-linux-amd64" tfsec \
       "18e2f947a4f0ec74bf6db07245fc81f83930835ef1b5d51d2d5152a6548b5e45"; \
    chmod +x tfsec; \
    # gosec 2.22.4
    dl "https://github.com/securego/gosec/releases/download/v2.22.4/gosec_2.22.4_linux_amd64.tar.gz" gosec.tgz \
       "2a7f67f720c20cb6922857fb474c095872ce4ec0364d1783347800bf0d5f22bf"; \
    tar -xzf gosec.tgz gosec; rm gosec.tgz; \
    # bearer 1.48.0
    dl "https://github.com/bearer/bearer/releases/download/v1.48.0/bearer_1.48.0_linux_amd64.tar.gz" bearer.tgz \
       "1fae001d04f00fe4dc3fb35b38295d33606d6bc59a3b8f8df1715dda8c7817cd"; \
    tar -xzf bearer.tgz bearer; rm bearer.tgz


# ── Stage 2: python-deps — Install Python packages into an isolated venv ──────
FROM python:3.14-slim AS python-deps

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY backend/requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt \
    && pip install --no-cache-dir --no-deps safety==2.3.5

COPY cyber-scanner/requirements.txt ./scanner-requirements.txt
RUN pip install --no-cache-dir -r scanner-requirements.txt


# ── Stage 3: final runtime image ──────────────────────────────────────────────
FROM python:3.14-slim AS final

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
