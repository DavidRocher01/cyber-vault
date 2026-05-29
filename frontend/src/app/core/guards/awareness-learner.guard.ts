import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AwarenessService } from '../../features/cyberscan/services/awareness.service';

export const awarenessLearnerGuard: CanActivateFn = () => {
  const awareness = inject(AwarenessService);
  const router = inject(Router);

  if (awareness.learnerSession()) {
    return true;
  }
  return router.createUrlTree(['/awareness/login']);
};
