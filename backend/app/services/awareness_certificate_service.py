"""
Certificate service — génération et vérification des attestations NIS2.

Flux :
  1. L'enrollment passe à "completed" (via progression service)
  2. issue_certificate() est appelé automatiquement
  3. Le PDF est généré (reportlab) avec QR code et signature SHA-256
  4. Le PDF est uploadé sur S3 (optionnel — si S3_BUCKET_NAME configuré)
  5. Un enregistrement AwarenessCertificate est créé en DB

Sécurité :
  - public_id : lisible (CERT-2026-A4B7C9) — affiché sur le PDF
  - verification_token : opaque (32 bytes urlsafe) — dans l'URL QR code
  - signature_hash : SHA-256(frozen_data_json + SECRET_KEY) — anti-falsification
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.awareness_certificate import AwarenessCertificate
from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_program import AwarenessProgram


# ── ID & signature ─────────────────────────────────────────────────────────────

def _generate_public_id() -> str:
    """CERT-YYYY-XXXXXX (6 uppercase hex chars)."""
    year = datetime.now(UTC).year
    suffix = secrets.token_hex(3).upper()
    return f"CERT-{year}-{suffix}"


def _compute_signature(frozen_data: str) -> str:
    """HMAC-SHA256(frozen_data_json, SECRET_KEY) → 64 hex chars."""
    return hmac.new(
        settings.SECRET_KEY.encode(),
        frozen_data.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(frozen_data: str, signature: str) -> bool:
    expected = _compute_signature(frozen_data)
    return hmac.compare_digest(expected, signature)


# ── Issue certificate ──────────────────────────────────────────────────────────

async def issue_certificate(
    db: AsyncSession,
    enrollment: AwarenessEnrollment,
) -> AwarenessCertificate:
    """
    Create (or return existing) certificate for a completed enrollment.
    Called automatically when enrollment.status → "completed".
    """
    existing = (
        await db.execute(
            select(AwarenessCertificate).where(
                AwarenessCertificate.enrollment_id == enrollment.id
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    learner = (
        await db.execute(select(AwarenessLearner).where(AwarenessLearner.id == enrollment.learner_id))
    ).scalar_one()
    program = (
        await db.execute(select(AwarenessProgram).where(AwarenessProgram.id == enrollment.program_id))
    ).scalar_one()

    # Frozen snapshot — immutable after issuance
    frozen = {
        "enrollment_id": enrollment.id,
        "learner_id": learner.id,
        "learner_email": learner.email,
        "learner_name": f"{learner.first_name or ''} {learner.last_name or ''}".strip() or learner.email,
        "program_id": program.id,
        "program_title": program.title,
        "program_version": program.version,
        "completion_pct": enrollment.completion_pct,
        "issued_at": datetime.now(UTC).isoformat(),
    }
    frozen_json = json.dumps(frozen, sort_keys=True)
    signature = _compute_signature(frozen_json)

    expires_at = None
    if program.certificate_validity_months > 0:
        expires_at = datetime.now(UTC) + timedelta(days=program.certificate_validity_months * 30)

    cert = AwarenessCertificate(
        enrollment_id=enrollment.id,
        learner_id=learner.id,
        public_id=_generate_public_id(),
        verification_token=secrets.token_urlsafe(32),
        signature_hash=signature,
        frozen_data_json=frozen_json,
        issued_at=datetime.now(UTC),
        expires_at=expires_at,
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)

    # Generate and attach PDF (S3 optional)
    try:
        pdf_bytes = generate_certificate_pdf(cert, frozen)
        s3_key = await _upload_to_s3(cert.public_id, pdf_bytes)
        if s3_key:
            cert.pdf_s3_key = s3_key
            await db.commit()
    except Exception:
        pass  # PDF generation is best-effort; certificate DB record always created

    return cert


# ── Verification ───────────────────────────────────────────────────────────────

async def verify_certificate(
    db: AsyncSession,
    public_id: str,
    token: str,
) -> dict | None:
    """
    Public verification — no auth required.
    Returns public-safe data or None if invalid/revoked/expired.
    """
    cert = (
        await db.execute(
            select(AwarenessCertificate).where(
                AwarenessCertificate.public_id == public_id,
                AwarenessCertificate.verification_token == token,
            )
        )
    ).scalar_one_or_none()
    if cert is None:
        return None
    if cert.is_revoked:
        return None
    if cert.expires_at and cert.expires_at < datetime.now(UTC):
        return None
    if not verify_signature(cert.frozen_data_json, cert.signature_hash):
        return None

    # Increment verification counter
    cert.verification_count += 1
    await db.commit()

    frozen = json.loads(cert.frozen_data_json)
    return {
        "valid": True,
        "public_id": cert.public_id,
        "learner_name": frozen.get("learner_name"),
        "program_title": frozen.get("program_title"),
        "issued_at": cert.issued_at.isoformat(),
        "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,
        "verification_count": cert.verification_count,
    }


# ── PDF generation ─────────────────────────────────────────────────────────────

def generate_certificate_pdf(cert: AwarenessCertificate, frozen: dict) -> bytes:
    """Generate attestation PDF with reportlab + QR code."""
    import io

    import qrcode
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

    from app.services.pdf_brand import CYAN, DARK_BG, GRAY, WHITE, get_styles

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    styles = get_styles()
    story = []

    # ── QR code ────────────────────────────────────────────────────────────────
    verify_url = (
        f"{settings.FRONTEND_URL}/verify-certificate"
        f"/{cert.public_id}?token={cert.verification_token}"
    )
    qr = qrcode.make(verify_url)
    qr_io = io.BytesIO()
    qr.save(qr_io, format="PNG")
    qr_io.seek(0)

    from reportlab.platypus import Image, Paragraph
    from reportlab.lib.styles import ParagraphStyle

    _navy = colors.HexColor("#0f172a")
    _cyan = CYAN
    _gray = GRAY
    _white = WHITE

    h1 = ParagraphStyle("cert_h1", fontSize=26, textColor=_cyan, fontName="Helvetica-Bold",
                         alignment=1, spaceAfter=4)
    sub = ParagraphStyle("cert_sub", fontSize=11, textColor=_gray, alignment=1, spaceAfter=16)
    body = ParagraphStyle("cert_body", fontSize=10, textColor=_white, leading=16, spaceAfter=4)
    label = ParagraphStyle("cert_label", fontSize=8, textColor=_gray, alignment=1)
    big_name = ParagraphStyle("cert_name", fontSize=20, textColor=_white, fontName="Helvetica-Bold",
                               alignment=1, spaceAfter=8)

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("ATTESTATION DE FORMATION", h1))
    story.append(Paragraph("Cybersécurité — Conformité NIS2 Article 21", sub))
    story.append(Spacer(1, 6 * mm))

    learner_name = frozen.get("learner_name", "")
    story.append(Paragraph("Décerné à", label))
    story.append(Paragraph(learner_name or "—", big_name))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(f"pour avoir complété le programme", body))
    story.append(Paragraph(f"<b>{frozen.get('program_title', '')}</b>", body))
    story.append(Spacer(1, 6 * mm))

    issued_str = cert.issued_at.strftime("%d/%m/%Y") if cert.issued_at else "—"
    expires_str = cert.expires_at.strftime("%d/%m/%Y") if cert.expires_at else "Sans expiration"

    data = [
        ["Référence", cert.public_id],
        ["Date d'émission", issued_str],
        ["Valable jusqu'au", expires_str],
        ["Score de complétion", f"{frozen.get('completion_pct', 0):.0f}%"],
    ]
    t = Table(data, colWidths=[60 * mm, 100 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1e293b")),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, -1), _white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
    ]))
    story.append(t)
    story.append(Spacer(1, 8 * mm))

    # QR code + verification note
    qr_img = Image(qr_io, width=30 * mm, height=30 * mm)
    qr_table = Table(
        [[qr_img, Paragraph(
            f"Vérifiez l'authenticité de cette attestation en scannant le QR code "
            f"ou en visitant :<br/><i>{verify_url[:80]}</i>",
            ParagraphStyle("verify", fontSize=7, textColor=_gray, leading=10),
        )]],
        colWidths=[35 * mm, 115 * mm],
    )
    qr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(qr_table)

    doc.build(story)
    return buf.getvalue()


# ── S3 upload ──────────────────────────────────────────────────────────────────

async def _upload_to_s3(public_id: str, pdf_bytes: bytes) -> str | None:
    """Upload PDF to S3 if configured. Returns S3 key or None."""
    if not settings.S3_BUCKET_NAME:
        return None
    try:
        import boto3
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        key = f"awareness/certificates/{public_id}.pdf"
        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        return key
    except Exception:
        return None
