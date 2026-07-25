import { MatSnackBar } from '@angular/material/snack-bar';

import { extractApiError } from './http-error';

/**
 * Affiche l'erreur d'API standard dans un snackbar.
 *
 * Factorise le handler d'erreur dupliqué ~18× dans les composants CRUD :
 * message extrait via {@link extractApiError}, bouton « Fermer », 4000 ms.
 * Comportement identique à l'ancien inline — aucun changement visible.
 */
export function snackApiError(snack: MatSnackBar, err: unknown, fallback = 'Erreur'): void {
  snack.open(extractApiError(err, fallback), 'Fermer', { duration: 4000 });
}
