import { HttpErrorResponse } from '@angular/common/http';

/**
 * Extrait un message d'erreur lisible d'une réponse HTTP d'API.
 *
 * Le backend renvoie ses erreurs sous la forme `{ detail: string }` (FastAPI).
 * Ce helper remplace le motif dupliqué ~65× dans l'app
 * (`err.error?.detail ?? 'fallback'`) en le typant correctement et en
 * garantissant qu'on ne rend jamais un objet brut (ex : `detail` = liste
 * d'erreurs de validation) : dans ce cas on retombe sur le message par défaut.
 */
export function extractApiError(err: unknown, fallback = 'Une erreur est survenue.'): string {
  const detail = (err as HttpErrorResponse | null)?.error?.detail;
  return typeof detail === 'string' && detail.trim().length > 0 ? detail : fallback;
}
