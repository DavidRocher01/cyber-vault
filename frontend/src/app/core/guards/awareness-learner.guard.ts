import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AwarenessSessionService } from '../services/awareness-session.service';

/**
 * Réserve le portail apprenant à qui détient une session.
 *
 * Ce garde dépendait du service métier de sensibilisation, dans `features/` —
 * le seul import de `core/` vers `features/` du projet. Il ne lui fallait
 * pourtant que l'état de session, désormais dans `core/services/`.
 */
export const awarenessLearnerGuard: CanActivateFn = () => {
  const sessions = inject(AwarenessSessionService);
  const router = inject(Router);

  if (sessions.session()) {
    return true;
  }
  return router.createUrlTree(['/awareness/login']);
};
