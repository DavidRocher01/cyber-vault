FROM python:3.12-slim

# Apply OS security patches + install system tools + all security scanners
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        curl wget git nodejs npm ca-certificates nmap \
    # gitleaks
    && GITLEAKS_VERSION=8.30.1 \
    && curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
       | tar -xz -C /usr/local/bin gitleaks \
    # trivy
    && TRIVY_VERSION=0.69.3 \
    && curl -sSfL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
       | tar -xz -C /usr/local/bin trivy \
    # trufflehog (git history secret scanning)
    && TRUFFLEHOG_VERSION=3.88.1 \
    && curl -sSfL "https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_amd64.tar.gz" \
       | tar -xz -C /usr/local/bin trufflehog \
    # grype (multi-ecosystem vulnerability scanner)
    && GRYPE_VERSION=0.90.0 \
    && curl -sSfL "https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}/grype_${GRYPE_VERSION}_linux_amd64.tar.gz" \
       | tar -xz -C /usr/local/bin grype \
    # osv-scanner (Google OSV database)
    && OSV_VERSION=1.9.2 \
    && curl -sSfL "https://github.com/google/osv-scanner/releases/download/v${OSV_VERSION}/osv-scanner_linux_amd64" \
       -o /usr/local/bin/osv-scanner && chmod +x /usr/local/bin/osv-scanner \
    # hadolint (Dockerfile linting)
    && HADOLINT_VERSION=2.12.0 \
    && curl -sSfL "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-Linux-x86_64" \
       -o /usr/local/bin/hadolint && chmod +x /usr/local/bin/hadolint \
    # tfsec (Terraform security)
    && TFSEC_VERSION=1.28.11 \
    && curl -sSfL "https://github.com/aquasecurity/tfsec/releases/download/v${TFSEC_VERSION}/tfsec-linux-amd64" \
       -o /usr/local/bin/tfsec && chmod +x /usr/local/bin/tfsec \
    # gosec (Go SAST)
    && GOSEC_VERSION=2.22.4 \
    && curl -sSfL "https://github.com/securego/gosec/releases/download/v${GOSEC_VERSION}/gosec_${GOSEC_VERSION}_linux_amd64.tar.gz" \
       | tar -xz -C /usr/local/bin gosec \
    # bearer (PII / data-flow security)
    && BEARER_VERSION=1.48.0 \
    && curl -sSfL "https://github.com/bearer/bearer/releases/download/v${BEARER_VERSION}/bearer_${BEARER_VERSION}_linux_amd64.tar.gz" \
       | tar -xz -C /usr/local/bin bearer \
    # eslint + security plugin (JS/TS SAST)
    && npm install -g eslint@8 eslint-plugin-security@3 --silent \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt \
    && pip install --no-cache-dir --no-deps safety==2.3.5

# Copy cyber-scanner and install its dependencies
COPY cyber-scanner/ /cyber-scanner/
RUN pip install --no-cache-dir -r /cyber-scanner/requirements.txt

COPY backend/ .

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
