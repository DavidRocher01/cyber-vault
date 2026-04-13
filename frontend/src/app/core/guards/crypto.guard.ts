import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { CryptoService } from '../services/crypto.service';

export const cryptoGuard: CanActivateFn = (route, state) => {
  const cryptoService = inject(CryptoService);
  const router = inject(Router);
  if (cryptoService.hasKey()) return true;
  return router.createUrlTree(['/auth/master-password'], { queryParams: { returnUrl: state.url } });
};
