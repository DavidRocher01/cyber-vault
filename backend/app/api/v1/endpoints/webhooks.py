"""
Stripe webhook handler.
Listens for subscription lifecycle events and updates DB accordingly.
"""

import asyncio
import json
from datetime import UTC, datetime

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.divers import StatusOut
from app.services import (
    acquisition_service,
    email_suppression,
    identite_fiscale,
    signature_svix,
    stripe_webhook_service,
    subscription_service,
    user_service,
)
from app.services.invoice_service import create_invoice
from app.services.stripe_service import construct_webhook_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/resend", response_model=StatusOut, include_in_schema=False)
async def resend_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Rebonds et plaintes signales par Resend.

    POURQUOI CET ENDPOINT. Rien n'ecoutait ce que Resend renvoyait : un e-mail
    qui rebondit ne laissait aucune trace. Or les fournisseurs de messagerie
    notent les expediteurs sur ce taux, et la sanction ne se voit pas — elle se
    manifeste le jour ou les e-mails LEGITIMES partent en indesirables.

    REPONDRE 200 MEME QUAND ON N'A RIEN FAIT est deliberé : Svix rejoue les
    livraisons non acquittees. Un evenement qu'on ignore volontairement — un
    rebond souple, un `email.delivered` — ne doit pas etre rejoue en boucle.
    Seule une signature invalide merite un refus.
    """
    corps = await request.body()

    if not signature_svix.verifier(
        settings.RESEND_WEBHOOK_SECRET,
        request.headers.get("svix-id"),
        request.headers.get("svix-timestamp"),
        request.headers.get("svix-signature"),
        corps,
    ):
        # Sans cette garde, n'importe qui pourrait faire cesser tout envoi vers
        # l'adresse de son choix, reinitialisation de mot de passe comprise.
        logger.warning("Webhook Resend refuse : signature invalide")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        evenement = json.loads(corps)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    await email_suppression.traiter_evenement(db, evenement)
    return {"status": "ok"}


@router.post("/stripe", response_model=StatusOut)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as e:
        logger.warning(f"Stripe webhook payload invalide: {type(e).__name__}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_id = event["id"]
    if await stripe_webhook_service.is_event_processed(db, event_id):
        return {"status": "ok"}

    data = event["data"]["object"]

    try:
        if event["type"] == "checkout.session.completed":
            await _handle_checkout_completed(data, db)

        elif event["type"] in (
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            await _handle_subscription_updated(data, db)

        elif event["type"] == "invoice.payment_succeeded":
            await _handle_invoice_payment_succeeded(data, db)

    except Exception as exc:
        logger.exception(f"Stripe webhook {event_id} processing failed: {exc}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    # Mark as processed only after successful handling so Stripe can retry on failure.
    # Ce commit persiste aussi tous les changements posés par les handlers ci-dessus
    # (même transaction) — atomicité traitement + marqueur d'idempotence.
    await stripe_webhook_service.mark_event_processed(db, event_id)
    return {"status": "ok"}


async def _handle_checkout_completed(session: dict, db: AsyncSession) -> None:
    """Create or update Subscription after successful checkout."""
    metadata = session.get("metadata") or {}

    # ── Add-on: extra site slots ──────────────────────────────────────────────
    if metadata.get("addon_type") == "extra_sites":
        user_id = metadata.get("user_id")
        if user_id:
            from app.core.config import settings

            sub = await subscription_service.get_active_subscription(db, int(user_id))
            if sub:
                stripe_webhook_service.increment_extra_sites(sub, settings.ADDON_EXTRA_SITES_COUNT)
        return

    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    customer_email = session.get("customer_details", {}).get("email")

    if not customer_id or not subscription_id:
        return

    # Retrieve full subscription to get price_id and period (async-safe)
    stripe_sub = await asyncio.to_thread(stripe.Subscription.retrieve, subscription_id)
    try:
        price_id = stripe_sub["items"]["data"][0]["price"]["id"]
    except (KeyError, IndexError) as exc:
        logger.error(
            f"Stripe webhook: cannot extract price_id from subscription {subscription_id}: {exc}"
        )
        return

    # Find matching plan
    plan = await stripe_webhook_service.get_plan_by_price_id(db, price_id)
    if not plan:
        logger.warning(
            f"Stripe webhook: no plan found for price_id={price_id} "
            f"(subscription_id={subscription_id}) — create a matching plan or update Stripe IDs"
        )
        return

    # Find user by email
    user = await user_service.get_by_email(db, customer_email)
    if not user:
        logger.error(
            f"Stripe webhook: user not found for subscription {subscription_id} "
            f"— subscription will not be activated"
        )
        return

    # Upsert subscription
    existing = await subscription_service.get_subscription(db, user.id)

    period_start = datetime.fromtimestamp(stripe_sub["current_period_start"], tz=UTC)
    period_end = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=UTC)

    stripe_webhook_service.upsert_checkout_subscription(
        db,
        existing=existing,
        user_id=user.id,
        plan_id=plan.id,
        customer_id=customer_id,
        subscription_id=subscription_id,
        period_start=period_start,
        period_end=period_end,
    )

    # Dernière étape du tunnel d'acquisition — enregistrée ICI et pas au clic sur
    # « s'abonner » : à ce clic, rien n'existe encore (onglet fermé, carte
    # refusée). Compter les intentions gonflerait le revenu attribué.
    #
    # MRR : pour un abonnement annuel, l'équivalent mensuel est le montant annuel
    # divisé par douze — soit dix mois payés sur douze, deux étant offerts.
    # Utiliser `price_eur` tel quel surestimerait de 20 %.
    annuel = bool(plan.stripe_price_id_yearly) and price_id == plan.stripe_price_id_yearly
    mrr_cents = round(plan.price_eur_yearly / 12) if annuel else plan.price_eur
    # `valider=False` : le webhook commit a la toute fin, avec son marqueur
    # d'idempotence. Valider ici casserait cette atomicite.
    await acquisition_service.enregistrer_abonnement(
        db, user_id=user.id, montant_mensuel_cents=mrr_cents, valider=False
    )


async def _handle_subscription_updated(stripe_sub: dict, db: AsyncSession) -> None:
    """Sync subscription status changes (canceled, past_due…)."""
    subscription_id = stripe_sub.get("id")
    if not subscription_id:
        return

    sub = await stripe_webhook_service.get_subscription_by_stripe_id(db, subscription_id)
    if not sub:
        return

    new_status = stripe_sub.get("status", sub.status)
    period_end = (
        datetime.fromtimestamp(stripe_sub["current_period_end"], tz=UTC)
        if stripe_sub.get("current_period_end")
        else None
    )
    stripe_webhook_service.apply_subscription_status(sub, status=new_status, period_end=period_end)


def _adresse_postale(adresse: dict | None) -> str | None:
    """Met l'adresse Stripe en une chaine imprimable, ou `None` si elle est vide.

    Stripe renvoie un dictionnaire dont chaque champ peut valoir `None`. Une
    concatenation naive produirait des lignes vides et des virgules orphelines
    sur la facture.
    """
    if not adresse:
        return None
    lignes = [
        adresse.get("line1"),
        adresse.get("line2"),
        " ".join(filter(None, [adresse.get("postal_code"), adresse.get("city")])).strip(),
        adresse.get("country"),
    ]
    retenues = [ligne for ligne in lignes if ligne and ligne.strip()]
    return "\n".join(retenues) or None


async def _handle_invoice_payment_succeeded(stripe_inv: dict, db: AsyncSession) -> None:
    """Auto-create a subscription invoice when Stripe confirms payment."""
    stripe_invoice_id = stripe_inv.get("id")
    customer_email = stripe_inv.get("customer_email") or (
        stripe_inv.get("customer_details") or {}
    ).get("email")
    amount_paid = stripe_inv.get("amount_paid", 0)  # cents

    if not stripe_invoice_id or not customer_email or amount_paid <= 0:
        return

    # Avoid duplicate invoices for the same Stripe invoice ID
    if await stripe_webhook_service.get_invoice_by_stripe_id(db, stripe_invoice_id):
        return

    # Resolve user
    user = await user_service.get_by_email(db, customer_email)

    # Build description from Stripe line items if available
    lines = stripe_inv.get("lines", {}).get("data", [])
    description = (
        lines[0].get("description", "Abonnement Rocher Cybersécurité")
        if lines
        else "Abonnement Rocher Cybersécurité"
    )

    invoice_date = datetime.fromtimestamp(
        stripe_inv.get("created", datetime.now(UTC).timestamp()),
        tz=UTC,
    ).date()

    # SIREN DE L'ACHETEUR, quand Stripe a collecte un numero de TVA francais.
    # Obligatoire sur les factures entre professionnels au 1er septembre 2027 ;
    # collecte des maintenant parce qu'une donnee non demandee au moment de la
    # vente ne se retrouve plus.
    client_siren = None
    for identifiant in stripe_inv.get("customer_tax_ids") or []:
        client_siren = identite_fiscale.siren_depuis_identifiant(
            identifiant.get("type"), identifiant.get("value")
        )
        if client_siren:
            break

    await create_invoice(
        db,
        user_id=user.id if user else None,
        type="subscription",
        client_name=stripe_inv.get("customer_name") or (user.email if user else customer_email),
        client_email=customer_email,
        # L'ADRESSE ETAIT JETEE. Stripe la collecte a la caisse
        # (`billing_address_collection`), et cette ligne passait `None` : aucune
        # facture emise jusqu'ici ne porte l'adresse du client, alors qu'elle
        # est une mention obligatoire.
        client_address=_adresse_postale(stripe_inv.get("customer_address")),
        client_siren=client_siren,
        description=description,
        amount_cents=amount_paid,
        status="paid",
        stripe_invoice_id=stripe_invoice_id,
        issue_date=invoice_date,
    )
