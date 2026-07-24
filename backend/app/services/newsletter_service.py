"""Service d'acces aux donnees newsletter (abonnes, planning, contenu editorial).

L'endpoint garde la generation/hachage des tokens, la construction des URLs et
l'envoi d'email ; ce service porte les requetes et les frontieres de
transaction. Les fonctions recoivent des valeurs deja preparees (hash de token,
dicts de champs), jamais un schema HTTP.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_setting import AppSetting
from app.models.newsletter_schedule import NewsletterScheduleItem
from app.models.newsletter_subscriber import NewsletterSubscriber

# ── Abonnes ─────────────────────────────────────────────────────────────────


async def get_subscriber_by_email(db: AsyncSession, email: str) -> NewsletterSubscriber | None:
    """Abonne par email, sinon None."""
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )
    return result.scalar_one_or_none()


async def get_by_confirmation_token(
    db: AsyncSession, token_hash: str
) -> NewsletterSubscriber | None:
    """Abonne par hash de token de confirmation, sinon None."""
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.confirmation_token == token_hash)
    )
    return result.scalar_one_or_none()


async def get_by_unsubscribe_token(db: AsyncSession, token: str) -> NewsletterSubscriber | None:
    """Abonne par token de desabonnement, sinon None."""
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.unsubscribe_token == token)
    )
    return result.scalar_one_or_none()


async def create_pending_subscriber(
    db: AsyncSession, *, email: str, confirmation_token_hash: str, unsubscribe_token: str
) -> NewsletterSubscriber:
    """Cree un abonne en attente de confirmation (inactif)."""
    subscriber = NewsletterSubscriber(
        email=email,
        subscribed_at=datetime.now(UTC),
        is_active=False,
        confirmation_token=confirmation_token_hash,
        unsubscribe_token=unsubscribe_token,
    )
    db.add(subscriber)
    await db.commit()
    return subscriber


async def refresh_confirmation(
    db: AsyncSession, subscriber: NewsletterSubscriber, confirmation_token_hash: str
) -> None:
    """Renouvelle le token de confirmation d'un abonne non confirme."""
    subscriber.confirmation_token = confirmation_token_hash
    subscriber.subscribed_at = datetime.now(UTC)
    await db.commit()


async def reactivate_subscriber(db: AsyncSession, subscriber: NewsletterSubscriber) -> None:
    """Reactive un abonne precedemment desabonne (deja confirme)."""
    subscriber.is_active = True
    subscriber.subscribed_at = datetime.now(UTC)
    await db.commit()


async def confirm_subscriber(db: AsyncSession, subscriber: NewsletterSubscriber) -> None:
    """Active un abonne apres confirmation de son email."""
    subscriber.is_active = True
    subscriber.confirmed_at = datetime.now(UTC)
    subscriber.confirmation_token = None
    await db.commit()


async def deactivate_subscriber(db: AsyncSession, subscriber: NewsletterSubscriber) -> None:
    """Desabonne un abonne."""
    subscriber.is_active = False
    await db.commit()


async def count_stats(db: AsyncSession) -> tuple[int, int, int]:
    """Renvoie (total, actifs, en_attente_confirmation)."""
    total_r = await db.execute(select(func.count()).select_from(NewsletterSubscriber))
    active_r = await db.execute(
        select(func.count())
        .select_from(NewsletterSubscriber)
        .where(NewsletterSubscriber.is_active == True)  # noqa: E712
    )
    pending_r = await db.execute(
        select(func.count())
        .select_from(NewsletterSubscriber)
        .where(
            NewsletterSubscriber.is_active == False,  # noqa: E712
            NewsletterSubscriber.confirmation_token != None,  # noqa: E711
        )
    )
    return total_r.scalar_one(), active_r.scalar_one(), pending_r.scalar_one()


async def list_subscribers(
    db: AsyncSession, *, skip: int, limit: int
) -> list[NewsletterSubscriber]:
    """Abonnes tries par date d'inscription decroissante (pagines)."""
    result = await db.execute(
        select(NewsletterSubscriber)
        .order_by(NewsletterSubscriber.subscribed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_active_subscribers(db: AsyncSession) -> list[NewsletterSubscriber]:
    """Abonnes actifs."""
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


# ── Planning ────────────────────────────────────────────────────────────────


async def list_schedule(db: AsyncSession) -> list[NewsletterScheduleItem]:
    """Items du planning tries par position."""
    result = await db.execute(
        select(NewsletterScheduleItem).order_by(NewsletterScheduleItem.position)
    )
    return list(result.scalars().all())


async def replace_schedule(db: AsyncSession, items: list[dict]) -> list[NewsletterScheduleItem]:
    """Remplace tout le planning par les items fournis (dicts de champs modele)."""
    now = datetime.now(UTC)
    existing = await db.execute(select(NewsletterScheduleItem))
    for row in existing.scalars().all():
        await db.delete(row)
    await db.flush()

    created: list[NewsletterScheduleItem] = []
    for item in sorted(items, key=lambda x: x["position"]):
        row = NewsletterScheduleItem(**item, updated_at=now)
        db.add(row)
        created.append(row)
    await db.commit()
    return created


# ── Contenu editorial (AppSetting) ────────────────────────────────────────────


async def get_content_setting(db: AsyncSession, key: str) -> AppSetting | None:
    """Reglage applicatif par cle, sinon None."""
    return await db.get(AppSetting, key)


async def upsert_content_setting(db: AsyncSession, key: str, value_text: str) -> None:
    """Cree ou met a jour la valeur texte d'un reglage applicatif."""
    setting = await db.get(AppSetting, key)
    if setting is None:
        setting = AppSetting(key=key, value_int=0, value_text=value_text)
        db.add(setting)
    else:
        setting.value_text = value_text
    await db.commit()
