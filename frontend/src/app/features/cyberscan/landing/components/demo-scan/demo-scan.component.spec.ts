/**
 * DemoScanComponent — lancement du scan public (états loading / résultat / erreur).
 * Service et Router mockés, aucun appel réseau.
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { PublicScanApiService } from '../../../services/public-scan-api.service';
import { DemoScanComponent } from './demo-scan.component';

function make() {
  const cyberscanMock = { createPublicScan: vi.fn() };
  const routerMock = { navigate: vi.fn() };
  const injector = Injector.create({
    providers: [
      { provide: PublicScanApiService, useValue: cyberscanMock },
      { provide: Router, useValue: routerMock },
    ],
  });
  const comp = runInInjectionContext(injector, () => new DemoScanComponent());
  return { comp, cyberscanMock, routerMock };
}

describe('DemoScanComponent — état initial', () => {
  it('demoUrl vide, non chargé, sans erreur', () => {
    const { comp } = make();
    expect(comp.demoUrl()).toBe('');
    expect(comp.demoLoading()).toBe(false);
    expect(comp.demoError()).toBeNull();
  });
});

describe('DemoScanComponent — submit() garde-fous', () => {
  it('ne fait rien si URL vide', () => {
    const { comp, cyberscanMock } = make();
    comp.submit();
    expect(cyberscanMock.createPublicScan).not.toHaveBeenCalled();
  });

  it('ne fait rien si URL uniquement des espaces', () => {
    const { comp, cyberscanMock } = make();
    comp.demoUrl.set('   ');
    comp.submit();
    expect(cyberscanMock.createPublicScan).not.toHaveBeenCalled();
    expect(comp.demoLoading()).toBe(false);
  });
});

describe('DemoScanComponent — submit() normalisation URL', () => {
  it('préfixe https:// si aucun schéma', () => {
    const { comp, cyberscanMock } = make();
    cyberscanMock.createPublicScan.mockReturnValue(of({ token: 't' }));
    comp.demoUrl.set('monsite.com');
    comp.submit();
    expect(cyberscanMock.createPublicScan).toHaveBeenCalledWith('https://monsite.com');
  });

  it('conserve un schéma https:// existant', () => {
    const { comp, cyberscanMock } = make();
    cyberscanMock.createPublicScan.mockReturnValue(of({ token: 't' }));
    comp.demoUrl.set('https://monsite.com');
    comp.submit();
    expect(cyberscanMock.createPublicScan).toHaveBeenCalledWith('https://monsite.com');
  });

  it('conserve un schéma http:// existant', () => {
    const { comp, cyberscanMock } = make();
    cyberscanMock.createPublicScan.mockReturnValue(of({ token: 't' }));
    comp.demoUrl.set('http://monsite.com');
    comp.submit();
    expect(cyberscanMock.createPublicScan).toHaveBeenCalledWith('http://monsite.com');
  });

  it('trim les espaces autour de l’URL', () => {
    const { comp, cyberscanMock } = make();
    cyberscanMock.createPublicScan.mockReturnValue(of({ token: 't' }));
    comp.demoUrl.set('  monsite.com  ');
    comp.submit();
    expect(cyberscanMock.createPublicScan).toHaveBeenCalledWith('https://monsite.com');
  });
});

describe('DemoScanComponent — submit() succès', () => {
  it('arrête le loading et navigue vers /demo-result avec le token', () => {
    const { comp, cyberscanMock, routerMock } = make();
    cyberscanMock.createPublicScan.mockReturnValue(of({ token: 'abc123' }));
    comp.demoUrl.set('https://monsite.com');
    comp.submit();
    expect(comp.demoLoading()).toBe(false);
    expect(comp.demoError()).toBeNull();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/demo-result', 'abc123']);
  });
});

describe('DemoScanComponent — submit() erreur', () => {
  it('affiche le détail renvoyé par le backend et coupe le loading', () => {
    const { comp, cyberscanMock, routerMock } = make();
    cyberscanMock.createPublicScan.mockReturnValue(
      throwError(() => ({ error: { detail: 'Quota atteint' } }))
    );
    comp.demoUrl.set('https://monsite.com');
    comp.submit();
    expect(comp.demoLoading()).toBe(false);
    expect(comp.demoError()).toBe('Quota atteint');
    expect(routerMock.navigate).not.toHaveBeenCalled();
  });

  it('affiche un message par défaut si aucun détail', () => {
    const { comp, cyberscanMock } = make();
    cyberscanMock.createPublicScan.mockReturnValue(throwError(() => ({ error: {} })));
    comp.demoUrl.set('https://monsite.com');
    comp.submit();
    expect(comp.demoLoading()).toBe(false);
    expect(comp.demoError()).toBe('Erreur lors du lancement du scan. Réessayez.');
  });
});
