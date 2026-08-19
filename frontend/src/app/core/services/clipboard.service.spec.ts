import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { Injector, PLATFORM_ID, runInInjectionContext } from '@angular/core';

import { ClipboardService } from './clipboard.service';

/**
 * Ce service etait EXCLU de la mesure de couverture, sans justification ecrite,
 * et n'avait aucun test : 18,2 % une fois l'exclusion levee le 2026-08-18.
 *
 * IL COMPTE PLUS QUE SA TAILLE NE LE LAISSE CROIRE. C'est lui qui met un mot de
 * passe du coffre dans le presse-papiers, et lui qui doit l'en retirer. Un
 * effacement qui ne partirait pas laisserait un secret disponible pour toute
 * autre application du poste, indefiniment.
 */
function creer(plateforme: 'browser' | 'server', avecPressePapiers = true) {
  const writeText = vi.fn().mockResolvedValue(undefined);
  const ancien = globalThis.navigator;

  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: avecPressePapiers ? { clipboard: { writeText } } : {},
  });

  const injector = Injector.create({
    providers: [
      { provide: PLATFORM_ID, useValue: plateforme },
      { provide: ClipboardService, useClass: ClipboardService },
    ],
  });
  const service = runInInjectionContext(injector, () => injector.get(ClipboardService));

  const restaurer = () =>
    Object.defineProperty(globalThis, 'navigator', { configurable: true, value: ancien });

  return { service, writeText, restaurer };
}

describe('ClipboardService', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('copie le texte demande', () => {
    const { service, writeText, restaurer } = creer('browser');

    service.copy('mot-de-passe');

    expect(writeText).toHaveBeenCalledWith('mot-de-passe');
    restaurer();
  });

  it('efface le presse-papiers apres le delai', () => {
    const { service, writeText, restaurer } = creer('browser');

    service.copy('secret', 30000);
    expect(writeText).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(29999);
    expect(writeText).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(1);
    expect(writeText).toHaveBeenLastCalledWith('');
    restaurer();
  });

  it('une seconde copie repousse l’effacement au lieu d’en cumuler deux', () => {
    // Sans annulation du minuteur precedent, le premier effacement viderait le
    // presse-papiers alors que la SECONDE valeur vient d'y etre posee.
    const { service, writeText, restaurer } = creer('browser');

    service.copy('premier', 30000);
    vi.advanceTimersByTime(20000);
    service.copy('second', 30000);

    vi.advanceTimersByTime(10001);
    expect(writeText).toHaveBeenLastCalledWith('second');

    vi.advanceTimersByTime(20000);
    expect(writeText).toHaveBeenLastCalledWith('');
    restaurer();
  });

  it('ne fait rien au prerendu', () => {
    const { service, writeText, restaurer } = creer('server');

    expect(() => service.copy('secret')).not.toThrow();
    expect(writeText).not.toHaveBeenCalled();
    restaurer();
  });

  it('ne fait rien si le navigateur n’expose pas de presse-papiers', () => {
    // Contexte non securise (http), ou navigateur ancien : `navigator.clipboard`
    // est absent. Le service doit se taire, pas exploser.
    const { service, writeText, restaurer } = creer('browser', false);

    expect(() => service.copy('secret')).not.toThrow();
    expect(writeText).not.toHaveBeenCalled();
    restaurer();
  });
});
