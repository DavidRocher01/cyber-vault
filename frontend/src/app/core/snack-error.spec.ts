import { describe, it, expect, vi } from 'vitest';
import { MatSnackBar } from '@angular/material/snack-bar';
import { snackApiError } from './snack-error';

describe('snackApiError', () => {
  it('ouvre un snackbar avec le detail API + Fermer + 4000ms', () => {
    const open = vi.fn();
    const snack = { open } as unknown as MatSnackBar;
    snackApiError(snack, { error: { detail: 'Boom' } });
    expect(open).toHaveBeenCalledWith('Boom', 'Fermer', { duration: 4000 });
  });

  it('retombe sur le fallback par defaut quand pas de detail', () => {
    const open = vi.fn();
    const snack = { open } as unknown as MatSnackBar;
    snackApiError(snack, {});
    expect(open).toHaveBeenCalledWith('Erreur', 'Fermer', { duration: 4000 });
  });

  it('accepte un fallback personnalise', () => {
    const open = vi.fn();
    const snack = { open } as unknown as MatSnackBar;
    snackApiError(snack, null, 'Echec');
    expect(open).toHaveBeenCalledWith('Echec', 'Fermer', { duration: 4000 });
  });
});
