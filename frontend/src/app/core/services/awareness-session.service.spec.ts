import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { Injector, PLATFORM_ID, runInInjectionContext } from '@angular/core';

import { AwarenessSessionService, type LearnerSession } from './awareness-session.service';

const CLE = 'awareness_learner_token';

function session(overrides: Partial<LearnerSession> = {}): LearnerSession {
  return {
    learner_id: 1,
    organization_id: 2,
    email: 'jane@acme.fr',
    first_name: 'Jane',
    last_name: 'Doe',
    access_token: 'tok-123',
    ...overrides,
  };
}

/** Construit le service pour une plateforme donnée — c'est tout l'enjeu ici. */
function creer(plateforme: 'browser' | 'server') {
  const injector = Injector.create({
    providers: [
      { provide: PLATFORM_ID, useValue: plateforme },
      { provide: AwarenessSessionService, useClass: AwarenessSessionService },
    ],
  });
  return runInInjectionContext(injector, () => injector.get(AwarenessSessionService));
}

describe('AwarenessSessionService — dans le navigateur', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it('démarre sans session quand le stockage est vide', () => {
    expect(creer('browser').session()).toBeNull();
  });

  it('relit une session valide au démarrage', () => {
    const s = session();
    localStorage.setItem(CLE, JSON.stringify(s));

    expect(creer('browser').session()).toEqual(s);
  });

  it('repart sans session si le contenu stocké est illisible', () => {
    // Un JSON corrompu ne doit pas empêcher l'application de démarrer.
    localStorage.setItem(CLE, '{pas-du-json');

    expect(creer('browser').session()).toBeNull();
  });

  it('enregistre la session dans le stockage ET dans le signal', () => {
    const service = creer('browser');
    const s = session({ access_token: 'jeton-enregistre' });

    service.enregistrer(s);

    expect(JSON.parse(localStorage.getItem(CLE)!)).toEqual(s);
    expect(service.session()).toEqual(s);
  });

  it('efface les deux à la déconnexion', () => {
    localStorage.setItem(CLE, JSON.stringify(session()));
    const service = creer('browser');

    service.effacer();

    expect(localStorage.getItem(CLE)).toBeNull();
    expect(service.session()).toBeNull();
  });
});

describe('AwarenessSessionService — au prérendu (pas de navigateur)', () => {
  /**
   * CE QUE CES TESTS DEFENDENT. La lecture se faisait dans un initialiseur de
   * champ d'un service `providedIn: 'root'` — donc a la construction, prerendu
   * compris, ou `localStorage` n'existe pas. Elle ne passait que grace au
   * `try/catch` qui l'entourait : protegee par accident. L'ecriture et
   * l'effacement, eux, n'avaient aucune protection.
   *
   * On rend donc `localStorage` explosif pour verifier qu'on n'y touche pas,
   * plutot que de se fier a l'absence d'erreur.
   */
  const vrai = globalThis.localStorage;

  beforeEach(() => {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      get() {
        throw new ReferenceError('localStorage is not defined');
      },
    });
  });

  afterEach(() => {
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: vrai });
  });

  it('démarre sans session, sans toucher au stockage', () => {
    expect(creer('server').session()).toBeNull();
  });

  it('enregistre en mémoire seulement', () => {
    const service = creer('server');
    const s = session();

    expect(() => service.enregistrer(s)).not.toThrow();
    expect(service.session()).toEqual(s);
  });

  it('efface en mémoire seulement', () => {
    const service = creer('server');
    service.enregistrer(session());

    expect(() => service.effacer()).not.toThrow();
    expect(service.session()).toBeNull();
  });
});
