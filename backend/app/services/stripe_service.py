"""
Stripe service — subscription lifecycle management.
Requires STRIPE_SECRET_KEY in .env
"""

import stripe

from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# Version d'API Stripe EPINGLEE explicitement.
#
# Sans cette ligne, la version d'API utilisee est celle par defaut du SDK — donc
# monter le SDK change AUSSI le contrat serveur (forme des payloads de webhook,
# champs des reponses) dans le meme commit. Deux risques melanges, impossibles a
# annuler separement.
#
# Avec l'epinglage, une montee du SDK devient un changement purement Python, et
# le passage a une version d'API plus recente devient une decision distincte,
# testable et reversible seule.
#
# Valeur = defaut du SDK 10.5.0, c'est-a-dire ce que la prod utilise deja :
# poser cette ligne ne change RIEN au comportement actuel.
STRIPE_API_VERSION = "2024-06-20"
stripe.api_version = STRIPE_API_VERSION


def create_customer(email: str) -> str:
    """Create a Stripe customer and return the customer ID."""
    customer = stripe.Customer.create(email=email)
    return customer.id


class PrixStripeIncoherentError(RuntimeError):
    """Le prix Stripe ne correspond pas a ce que l'application s'apprete a facturer."""


def _intervalle(recurrence: object) -> str | None:
    """Periodicite d'un prix, quelle que soit la forme rendue par le SDK.

    `Price.recurring` est type `Recurring | dict`. A l'execution c'est un
    StripeObject, qui derive de dict — d'ou le `.get()` qui fonctionnait tout en
    faisant echouer mypy sur la branche `Recurring`. On lit les deux formes
    plutot que de parier sur l'une.
    """
    if recurrence is None:
        return None
    if isinstance(recurrence, dict):
        valeur = recurrence.get("interval")
    else:
        valeur = getattr(recurrence, "interval", None)
    return valeur if isinstance(valeur, str) else None


def verifier_prix(price_id: str, montant_attendu: int, intervalle_attendu: str) -> None:
    """Compare le prix Stripe a ce qui a ete montre au client. Leve si ca diverge.

    Un `stripe_price_id` n'est qu'une chaine en base : rien n'empeche qu'il
    designe un tarif d'une generation precedente. C'est arrive — sept prix
    perimes sont restes actifs chez Stripe jusqu'au 2026-08-02, dont deux
    encore referencees par des migrations. Un checkout aurait alors debite
    9,90 EUR un abonnement affiche 49 EUR, sans la moindre erreur.

    D'ou ce controle, appele juste avant chaque creation de session : on refuse
    de facturer plutot que de facturer le mauvais montant. Cout : un appel API
    supplementaire par clic sur « s'abonner », ce qui est rare.

    `montant_attendu` est en centimes, `intervalle_attendu` vaut 'month' ou 'year'.
    """
    from app.core.pricing import COMPORTEMENT_TVA_ATTENDU

    prix = stripe.Price.retrieve(price_id)
    intervalle = _intervalle(prix.recurring)
    ecarts = []

    if not prix.active:
        ecarts.append("prix archive chez Stripe")
    if prix.unit_amount != montant_attendu:
        ecarts.append(f"montant {prix.unit_amount}c au lieu de {montant_attendu}c")
    if (prix.currency or "").lower() != "eur":
        ecarts.append(f"devise {prix.currency} au lieu de eur")
    if intervalle != intervalle_attendu:
        ecarts.append(f"intervalle {intervalle} au lieu de {intervalle_attendu}")
    if prix.tax_behavior != COMPORTEMENT_TVA_ATTENDU:
        ecarts.append(f"tax_behavior {prix.tax_behavior} au lieu de {COMPORTEMENT_TVA_ATTENDU}")

    if ecarts:
        raise PrixStripeIncoherentError(f"{price_id} : " + " ; ".join(ecarts))


def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    montant_attendu: int,
    intervalle_attendu: str,
    metadata: dict | None = None,
) -> str:
    """Create a Stripe Checkout Session and return the URL.

    `montant_attendu` / `intervalle_attendu` sont OBLIGATOIRES : on ne peut pas
    ouvrir un paiement sans declarer ce qu'on croit facturer. C'est le seul
    moyen de garantir que le debit correspond a l'affichage.
    """
    verifier_prix(price_id, montant_attendu, intervalle_attendu)
    kwargs: dict = dict(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        automatic_tax={"enabled": True},
        billing_address_collection="auto",
        # `name: auto` enregistre la DENOMINATION LEGALE saisie a la caisse, et
        # pas seulement le nom du payeur : c'est elle qui doit figurer sur une
        # facture entre professionnels.
        customer_update={"address": "auto", "name": "auto"},
        # SIREN DE L'ACHETEUR — obligatoire au 1er septembre 2027 sur les
        # factures entre professionnels. Stripe collecte un numero de TVA ; pour
        # la France, le SIREN en est les neuf derniers chiffres (voir
        # `identite_fiscale.py`).
        #
        # `if_supported` rend la saisie OBLIGATOIRE dans les pays ou le format
        # existe, et n'affiche rien ailleurs : un client hors zone n'est pas
        # bloque par une obligation qui ne le concerne pas.
        #
        # A savoir : Stripe ne redemande pas l'identifiant a un client qui en a
        # deja un d'enregistre. Les clients professionnels anterieurs a ce jour
        # ne seront donc pas sollicites automatiquement — il faudra les relancer.
        tax_id_collection={"enabled": True, "required": "if_supported"},
    )
    if metadata:
        kwargs["metadata"] = metadata
    session = stripe.checkout.Session.create(**kwargs)
    return session.url


def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe Billing Portal session and return the URL."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def cancel_subscription(subscription_id: str) -> None:
    """Cancel a Stripe subscription immediately."""
    stripe.Subscription.cancel(subscription_id)


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Validate and parse a Stripe webhook event."""
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
