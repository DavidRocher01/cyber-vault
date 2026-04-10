/**
 * NavHistoryService — tests de la logique de navigation.
 * Le service utilise l'injection constructeur (router uniquement).
 * back()/forward() utilisent router.navigateByUrl() et persistant dans sessionStorage.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Subject } from 'rxjs';
import { NavigationEnd } from '@angular/router';
import { NavHistoryService } from './nav-history.service';

const STORAGE_KEY = 'cvault_nav_history';

function makeService() {
  sessionStorage.clear();
  const events$ = new Subject<any>();
  const router: any = {
    events: events$,
    navigateByUrl: vi.fn().mockResolvedValue(true),
  };
  const service = new NavHistoryService(router);
  return { service, router, events$ };
}

function navigate(events$: Subject<any>, url: string) {
  events$.next(new NavigationEnd(0, url, url));
}

// ── État initial ───────────────────────────────────────────────────────────────

describe('NavHistoryService — état initial', () => {
  it('canGoBack est false au démarrage', () => {
    const { service } = makeService();
    expect(service.canGoBack()).toBe(false);
  });

  it('canGoForward est false au démarrage', () => {
    const { service } = makeService();
    expect(service.canGoForward()).toBe(false);
  });
});

// ── Navigation ─────────────────────────────────────────────────────────────────

describe('NavHistoryService — navigation', () => {
  it('canGoBack est true après avoir navigué vers deux pages', () => {
    const { service, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    expect(service.canGoBack()).toBe(true);
  });

  it('canGoBack reste false après une seule navigation', () => {
    const { service, events$ } = makeService();
    navigate(events$, '/page-a');
    expect(service.canGoBack()).toBe(false);
  });

  it('n\'ajoute pas la même URL deux fois de suite', () => {
    const { service, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-a');
    expect(service.canGoBack()).toBe(false);
  });
});

// ── back() ─────────────────────────────────────────────────────────────────────

describe('NavHistoryService — back()', () => {
  it('back() appelle router.navigateByUrl() avec l\'URL précédente', () => {
    const { service, router, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    service.back();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/page-a');
  });

  it('back() ne fait rien si canGoBack est false', () => {
    const { service, router, events$ } = makeService();
    navigate(events$, '/page-a');
    service.back();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it('back() décrémente la position', () => {
    const { service, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    service.back();
    expect(service.canGoForward()).toBe(true);
  });

  it('back() rend canGoBack false si on est au début', () => {
    const { service, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    service.back();
    expect(service.canGoBack()).toBe(false);
  });
});

// ── forward() ──────────────────────────────────────────────────────────────────

describe('NavHistoryService — forward()', () => {
  it('forward() ne fait rien si canGoForward est false', () => {
    const { service, router, events$ } = makeService();
    navigate(events$, '/page-a');
    service.forward();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it('forward() appelle router.navigateByUrl() avec l\'URL suivante après un back()', async () => {
    const { service, router, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    service.back();
    // Attendre que tous les microtasks soient résolus (jumping = false)
    await new Promise(resolve => setTimeout(resolve, 0));
    service.forward();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/page-b');
  });

  it('canGoForward est false quand on est à la dernière page du stack', () => {
    const { service, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    // Déjà en bout de stack — pas de forward possible
    expect(service.canGoForward()).toBe(false);
  });
});

// ── Persistance sessionStorage ─────────────────────────────────────────────────

describe('NavHistoryService — persistance sessionStorage', () => {
  beforeEach(() => sessionStorage.clear());

  it('sauvegarde le stack dans sessionStorage après chaque navigation', () => {
    const { events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    const stored = sessionStorage.getItem(STORAGE_KEY);
    expect(stored).toBeTruthy();
    expect(JSON.parse(stored!)).toEqual(['/page-a', '/page-b']);
  });

  it('restaure le stack depuis sessionStorage au démarrage', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(['/page-a', '/page-b']));
    const events$ = new Subject<any>();
    const router: any = { events: events$, navigateByUrl: vi.fn().mockResolvedValue(true) };
    const service = new NavHistoryService(router);
    // pos = stack.length - 1 = 1 → canGoBack = true
    expect(service.canGoBack()).toBe(true);
  });

  it('fonctionne sans sessionStorage (storage corrompu)', () => {
    sessionStorage.setItem(STORAGE_KEY, 'invalid-json{{{');
    const events$ = new Subject<any>();
    const router: any = { events: events$, navigateByUrl: vi.fn().mockResolvedValue(true) };
    // Ne doit pas lever d'exception
    expect(() => new NavHistoryService(router)).not.toThrow();
  });

  it('sauvegarde le stack après un back()', () => {
    const { service, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    service.back();
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY)!);
    expect(stored).toEqual(['/page-a', '/page-b']);
  });
});
