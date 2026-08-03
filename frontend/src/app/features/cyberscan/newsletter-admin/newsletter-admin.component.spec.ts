import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { FormArray, FormBuilder } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { NewsletterAdminComponent } from './newsletter-admin.component';

const STATS = { total: 10, active: 8, pending_confirmation: 2 };
const ARTICLES = [
  {
    position: 1,
    actu_title: 'Titre 1',
    actu_url: 'https://a.com',
    actu_source: 'Source A',
    reflex: 'Note 1',
    image_url: null,
  },
  {
    position: 2,
    actu_title: 'Titre 2',
    actu_url: 'https://b.com',
    actu_source: 'Source B',
    reflex: 'Note 2',
    image_url: null,
  },
];

/**
 * Faux service d'accès back-office. Depuis le 2026-08-03 le composant ne demande
 * plus de clé : il interroge `AdminAuthService`, comme les autres écrans admin.
 */
function fauxAdminAuth(estAdmin: boolean) {
  const authenticated = signal(false);
  return {
    authenticated,
    verificationEnCours: signal(false),
    verifierCompte: vi.fn(() => {
      authenticated.set(estAdmin);
      return of(estAdmin);
    }),
    logout: vi.fn(() => authenticated.set(false)),
  };
}

function make(estAdmin = true) {
  const comp = Object.create(NewsletterAdminComponent.prototype) as NewsletterAdminComponent;
  (comp as any).adminAuth = fauxAdminAuth(estAdmin);
  (comp as any).stats = signal(null);
  (comp as any).sending = signal(false);
  (comp as any).savingSchedule = signal(false);
  (comp as any).saveOk = signal(false);
  (comp as any).sendResult = signal(null);
  (comp as any).editionNumber = 1;
  const fb = new FormBuilder();
  (comp as any).fb = fb;
  const slot = (pos: number) =>
    fb.group({
      position: [pos],
      actu_source: ['x'],
      actu_title: ['x'],
      actu_url: ['x'],
      reflex: ['x'],
      image_url: [null],
    });
  (comp as any).scheduleForm = fb.group({
    articles: fb.array(Array.from({ length: 6 }, (_, i) => slot(i + 1))),
  });
  return comp;
}

describe('NewsletterAdminComponent — ngOnInit()', () => {
  it('charge les données quand le compte est administrateur', () => {
    const comp = make(true);
    (comp as any).http = {
      get: vi.fn((url: string) => (url.includes('stats') ? of(STATS) : of([]))),
    };
    comp.ngOnInit();
    expect(comp.stats()).toEqual(STATS);
  });

  it("ne demande rien au serveur quand le compte n'est pas administrateur", () => {
    const comp = make(false);
    const getSpy = vi.fn().mockReturnValue(of(STATS));
    (comp as any).http = { get: getSpy };
    comp.ngOnInit();
    expect(getSpy).not.toHaveBeenCalled();
    expect(comp.stats()).toBeNull();
  });
});

describe('NewsletterAdminComponent — plus aucune trace de la clé partagée', () => {
  // Garde-fou. Cette page a survécu au retrait de `X-Admin-Key` : elle envoyait
  // encore l'en-tête et exigeait une saisie, alors que le serveur ne l'acceptait
  // plus et que l'intercepteur posait déjà le jeton. Résultat, un écran qui
  // avait l'air de protéger quelque chose et que n'importe quelle chaîne
  // ouvrait.
  //
  // On lit le FICHIER et non `Component.toString()` : celui-ci ne rend que le
  // corps de classe (~3,4 kio), pas le gabarit, où se trouvait justement le
  // formulaire de saisie. Vérifié le 2026-08-03.
  it('ne contient plus ni saisie de clé, ni en-tête maison, ni stockage local', () => {
    // Chemin depuis la racine du frontend : sous jsdom, `import.meta.url` est
    // une URL http, pas file — `new URL(...)` y échoue.
    const source = readFileSync(
      resolve(
        process.cwd(),
        'src/app/features/cyberscan/newsletter-admin/newsletter-admin.component.ts'
      ),
      'utf8'
    );
    const corpsEtGabarit = source.slice(source.indexOf('@Component'));
    expect(corpsEtGabarit).not.toContain('X-Admin-Key');
    expect(corpsEtGabarit).not.toContain('admin_key');
    expect(corpsEtGabarit).not.toContain('sessionStorage');
  });

  it('ne conserve aucune méthode de la clé partagée', () => {
    const comp = make();
    expect((comp as any).submitKey).toBeUndefined();
    expect((comp as any).headers).toBeUndefined();
  });
});

describe('NewsletterAdminComponent — loadSchedule()', () => {
  it('pré-remplit les slots avec les articles existants', () => {
    const comp = make();
    (comp as any).http = { get: vi.fn().mockReturnValue(of(ARTICLES)) };
    comp.loadSchedule();
    const arr = (comp as any).scheduleForm.get('articles') as FormArray;
    expect(arr.at(0).value.actu_title).toBe('Titre 1');
    expect(arr.at(1).value.actu_source).toBe('Source B');
  });

  it('laisse les slots vides pour les positions sans article', () => {
    const comp = make();
    (comp as any).http = { get: vi.fn().mockReturnValue(of([])) };
    comp.loadSchedule();
    const arr = (comp as any).scheduleForm.get('articles') as FormArray;
    expect(arr.at(0).value.actu_title).toBe('');
  });
});

describe('NewsletterAdminComponent — saveSchedule()', () => {
  it('envoie uniquement les slots remplis', () => {
    const comp = make();
    const putSpy = vi.fn().mockReturnValue(of([]));
    (comp as any).http = { put: putSpy };
    comp.saveSchedule();
    const body = putSpy.mock.calls[0][1];
    expect(body.length).toBe(6);
    expect(comp.saveOk()).toBe(true);
  });

  it('ignore les slots vides (champs tous vides)', () => {
    const comp = make();
    const arr = (comp as any).scheduleForm.get('articles') as FormArray;
    arr.at(2).patchValue({ actu_title: '', actu_url: '', actu_source: '', reflex: '' });
    const putSpy = vi.fn().mockReturnValue(of([]));
    (comp as any).http = { put: putSpy };
    comp.saveSchedule();
    const body = putSpy.mock.calls[0][1];
    expect(body.length).toBe(5);
    expect(body.every((a: any) => a.actu_title)).toBe(true);
  });
});

describe('NewsletterAdminComponent — sendFromSchedule()', () => {
  it('envoie et affiche le message de succès', () => {
    const comp = make();
    (comp as any).http = {
      post: vi
        .fn()
        .mockReturnValue(of({ sent: 8, message: 'Édition #001 envoyée à 8 abonné(s).' })),
    };
    comp.sendFromSchedule();
    expect(comp.sendResult()?.ok).toBe(true);
  });

  it('affiche une erreur si le backend échoue', () => {
    const comp = make();
    (comp as any).http = { post: vi.fn().mockReturnValue(throwError(() => new Error('500'))) };
    comp.sendFromSchedule();
    expect(comp.sendResult()?.ok).toBe(false);
  });
});

describe('NewsletterAdminComponent — logout()', () => {
  it('referme le back-office et vide les données affichées', () => {
    const comp = make();
    (comp as any).adminAuth.authenticated.set(true);
    (comp as any).stats.set(STATS);
    comp.logout();
    expect((comp as any).adminAuth.authenticated()).toBe(false);
    expect(comp.stats()).toBeNull();
  });
});
