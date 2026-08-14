import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Injector, PLATFORM_ID, runInInjectionContext } from '@angular/core';

import { NotificationsService } from './notifications.service';

function creer(plateforme: 'browser' | 'server') {
  const injector = Injector.create({
    providers: [{ provide: PLATFORM_ID, useValue: plateforme }],
  });
  return runInInjectionContext(injector, () => new NotificationsService());
}

describe('NotificationsService', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('affiche un message par ton, avec le bon ton', () => {
    const s = creer('browser');

    s.success('Entrée mise à jour');
    s.error('Erreur de déchiffrement');
    s.warning('Trop de requêtes');

    expect(s.actives().map(n => [n.ton, n.texte])).toEqual([
      ['succes', 'Entrée mise à jour'],
      ['erreur', 'Erreur de déchiffrement'],
      ['avertissement', 'Trop de requêtes'],
    ]);
  });

  it('retire le message tout seul au bout de trois secondes', () => {
    const s = creer('browser');
    s.success('Export téléchargé');
    expect(s.actives()).toHaveLength(1);

    vi.advanceTimersByTime(2999);
    expect(s.actives()).toHaveLength(1);

    vi.advanceTimersByTime(1);
    expect(s.actives()).toHaveLength(0);
  });

  it('se ferme a la demande, et le minuteur ne rouvre rien', () => {
    const s = creer('browser');
    s.error('Erreur de déchiffrement');
    const id = s.actives()[0].id;

    s.fermer(id);
    expect(s.actives()).toHaveLength(0);

    // Si `fermer` n'annulait pas le minuteur, celui-ci s'executerait dans le
    // vide — inoffensif ici, mais le meme oubli sur un identifiant reattribue
    // fermerait une notification qui vient d'apparaitre.
    expect(() => vi.advanceTimersByTime(3000)).not.toThrow();
    expect(s.actives()).toHaveLength(0);
  });

  it("n'empile pas le meme message, et repousse celui deja visible", () => {
    const s = creer('browser');

    // Six requetes en parallele refusees en 429 : l'intercepteur appelle six
    // fois `warning` avec la meme phrase.
    for (let i = 0; i < 6; i++) {
      s.warning('Trop de requêtes. Réessayez dans quelques instants.');
    }
    expect(s.actives()).toHaveLength(1);

    // Deux secondes plus tard un septieme 429 arrive : l'echeance repart de
    // zero, la phrase ne disparait donc pas a la troisieme seconde.
    vi.advanceTimersByTime(2000);
    s.warning('Trop de requêtes. Réessayez dans quelques instants.');
    vi.advanceTimersByTime(1500);
    expect(s.actives()).toHaveLength(1);

    vi.advanceTimersByTime(1500);
    expect(s.actives()).toHaveLength(0);
  });

  it('distingue deux tons portant le meme texte', () => {
    const s = creer('browser');
    s.success('Terminé');
    s.error('Terminé');
    expect(s.actives()).toHaveLength(2);
  });

  it("n'affiche rien cote serveur et n'y arme aucun minuteur", () => {
    // CE TEST EST LE PLUS UTILE DU FICHIER. L'intercepteur HTTP appelle
    // `warning()` sur un 429, y compris pendant le prerendu des 40 routes. Un
    // `setTimeout` de trois secondes y retiendrait la stabilite de
    // l'application : le prerendu attendrait chaque minuteur avant d'ecrire la
    // page. Rien ne l'aurait signale — la page serait juste plus lente a
    // produire, et personne ne saurait pourquoi.
    const s = creer('server');
    const arme = vi.spyOn(globalThis, 'setTimeout');

    s.success('Entrée mise à jour');
    s.error('Erreur de déchiffrement');
    s.warning('Trop de requêtes');

    expect(s.actives()).toHaveLength(0);
    expect(arme).not.toHaveBeenCalled();
    arme.mockRestore();
  });
});
