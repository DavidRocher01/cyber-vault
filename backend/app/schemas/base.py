from pydantic import BaseModel


class StrictModel(BaseModel):
    """Base des schémas d'entrée exposés publiquement.

    Centralise ``extra='forbid'`` (règle de validation stricte du CLAUDE.md :
    tout schéma exposé publiquement rejette les champs non déclarés) afin
    d'éviter de répéter ``model_config = {"extra": "forbid"}`` dans chaque
    schéma d'input. Les schémas de réponse (lecture depuis l'ORM) continuent
    d'hériter directement de ``BaseModel`` avec ``from_attributes``.
    """

    model_config = {"extra": "forbid"}
