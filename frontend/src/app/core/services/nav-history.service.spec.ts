/**
 * NavHistoryService — tests de la logique de navigation.
 * Le service utilise l'injection constructeur (pas inject()),
 * on peut donc l'instancier directement avec des mocks.
 */
import { describe, it, expect, vi } from 'vitest';
import { Subject } from 'rxjs';
import { NavigationEnd } from '@angular/router';
import { NavHistoryService } from './nav-history.service';

function makeService() {
  const events$ = new Subject<any>();
  const router: any = { events: events$ };
  const location: any = { back: vi.fn(), forward: vi.fn() };
  const service = new NavHistoryService(router, location);
  return { service, router, location, events$ };
}

function navigate(events$: Subject<any>, url: string) {
  events$.next(new NavigationEnd(0, url, url));
}

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

describe('NavHistoryService — back()', () => {
  it('back() appelle location.back()', () => {
    const { service, location, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    service.back();
    expect(location.back).toHaveBeenCalled();
  });

  it('back() ne fait rien si canGoBack est false', () => {
    const { service, location, events$ } = makeService();
    navigate(events$, '/page-a');
    service.back(); // only one page, can't go back
    expect(location.back).not.toHaveBeenCalled();
  });

  it('back() décrémente la position', () => {
    const { service, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    service.back();
    // After going back, canGoForward should be true
    expect(service.canGoForward()).toBe(true);
  });
});

describe('NavHistoryService — forward()', () => {
  it('forward() ne fait rien si canGoForward est false', () => {
    const { service, location, events$ } = makeService();
    navigate(events$, '/page-a');
    service.forward();
    expect(location.forward).not.toHaveBeenCalled();
  });

  it('forward() appelle location.forward() après un back()', () => {
    vi.useFakeTimers();
    const { service, location, events$ } = makeService();
    navigate(events$, '/page-a');
    navigate(events$, '/page-b');
    service.back();
    vi.advanceTimersByTime(200); // reset jumping flag
    service.forward();
    expect(location.forward).toHaveBeenCalled();
    vi.useRealTimers();
  });
});
