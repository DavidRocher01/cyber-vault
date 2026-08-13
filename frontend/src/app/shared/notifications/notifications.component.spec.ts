import { describe, it, expect } from 'vitest';
import { Injector, PLATFORM_ID, runInInjectionContext } from '@angular/core';

import { NotificationsComponent } from './notifications.component';
import { NotificationsService, type TonNotification } from '../../core/notifications.service';

function creer() {
  const injector = Injector.create({
    // `useClass` et non `useValue: new NotificationsService()` : le constructeur
    // du service appelle `inject(PLATFORM_ID)`, or un `useValue` s'evalue hors
    // contexte d'injection.
    providers: [
      { provide: PLATFORM_ID, useValue: 'browser' },
      { provide: NotificationsService, useClass: NotificationsService },
    ],
  });
  return runInInjectionContext(injector, () => new NotificationsComponent());
}

describe('NotificationsComponent', () => {
  const TONS: TonNotification[] = ['succes', 'erreur', 'avertissement'];

  it('donne une icone et une teinte distinctes a chaque ton', () => {
    const c = creer();

    const icones = TONS.map(t => c.icone(t));
    const teintes = TONS.map(t => c.teinte(t));

    // Un `Record` incomplet renverrait `undefined` : la notification
    // s'afficherait sans icone ni couleur, donc sans distinguer une reussite
    // d'une erreur.
    expect(icones.every(Boolean)).toBe(true);
    expect(new Set(icones).size).toBe(TONS.length);
    expect(new Set(teintes).size).toBe(TONS.length);
  });

  it('expose les notifications actives du service', () => {
    const c = creer();
    expect(c.service.actives()).toHaveLength(0);

    c.service.error('Erreur de déchiffrement');
    expect(c.service.actives().map(n => n.texte)).toEqual(['Erreur de déchiffrement']);
  });
});
