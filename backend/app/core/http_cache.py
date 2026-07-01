"""Helpers de cache HTTP.

⚠️ À n'utiliser QUE sur des endpoints **publics, read-only, non personnalisés**.
JAMAIS sur une réponse authentifiée ou personnalisée : le CDN (CloudFront) servirait
la réponse d'un utilisateur à un autre (fuite de données).
"""

from collections.abc import Callable

from fastapi import Response


def cache_public(max_age: int) -> Callable[[Response], None]:
    """Dépendance FastAPI qui marque la réponse comme cacheable (navigateur + CDN).

    `max-age` (navigateur) et `s-maxage` (CDN) sont fixés à la même valeur.
    """

    def _set(response: Response) -> None:
        response.headers["Cache-Control"] = f"public, max-age={max_age}, s-maxage={max_age}"

    return _set
