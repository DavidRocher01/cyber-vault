from pydantic import BaseModel, Field


class ProvenanceIn(BaseModel):
    """Provenance déclarée par le client, à joindre à une conversion.

    Champs facultatifs, ajoutés aux schémas d'entrée des points de conversion
    (scan gratuit, inscription). Absents, la conversion est comptée en
    « direct » — la mesure ne doit jamais conditionner l'action.

    Les valeurs sont **normalisées côté serveur** avant écriture
    (`acquisition_service.normaliser`) : les longueurs déclarées ici ne sont
    qu'un premier filet, pas la garantie. Ne jamais stocker ces chaînes brutes.

    Aucun identifiant de visiteur n'est accepté, et il ne faut pas en ajouter :
    c'est ce qui dispense de bandeau de consentement (cf. `docs/ANALYTICS.md`).
    """

    utm_source: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)
    # Route d'entrée sur le site, pas une URL externe : le serveur n'en garde
    # que le chemin.
    page_atterrissage: str | None = Field(default=None, max_length=256)
