import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ScanGratuitComponent } from './scan-gratuit.component';

function makeComponent(): ScanGratuitComponent {
  return Object.create(ScanGratuitComponent.prototype) as ScanGratuitComponent;
}

describe('ScanGratuitComponent — moduleIcon()', () => {
  it('retourne check_circle pour OK', () => {
    expect(makeComponent().moduleIcon('OK')).toBe('check_circle');
  });

  it('retourne warning pour WARNING', () => {
    expect(makeComponent().moduleIcon('WARNING')).toBe('warning');
  });

  it('retourne cancel pour CRITICAL', () => {
    expect(makeComponent().moduleIcon('CRITICAL')).toBe('cancel');
  });

  it('retourne help_outline pour null', () => {
    expect(makeComponent().moduleIcon(null)).toBe('help_outline');
  });

  it('retourne help_outline pour statut inconnu', () => {
    expect(makeComponent().moduleIcon('UNKNOWN')).toBe('help_outline');
  });
});

describe('ScanGratuitComponent — moduleColor()', () => {
  it('retourne green pour OK', () => {
    expect(makeComponent().moduleColor('OK')).toContain('green');
  });

  it('retourne yellow pour WARNING', () => {
    expect(makeComponent().moduleColor('WARNING')).toContain('yellow');
  });

  it('retourne red pour CRITICAL', () => {
    expect(makeComponent().moduleColor('CRITICAL')).toContain('red');
  });

  it('retourne gray pour null', () => {
    expect(makeComponent().moduleColor(null)).toContain('gray');
  });

  it('retourne gray pour statut inconnu', () => {
    expect(makeComponent().moduleColor('UNKNOWN')).toContain('gray');
  });
});

describe('ScanGratuitComponent — get modules', () => {
  function withScan(results_json: string | null | undefined): ScanGratuitComponent {
    const c = makeComponent();
    (c as any).scan = signal(results_json === undefined ? null : { results_json });
    return c;
  }

  it('retourne [] quand aucun scan', () => {
    const c = makeComponent();
    (c as any).scan = signal(null);
    expect(c.modules).toEqual([]);
  });

  it('retourne [] quand results_json absent', () => {
    expect(withScan(undefined).modules).toEqual([]);
  });

  it('retourne [] quand JSON invalide', () => {
    expect(withScan('{pas du json').modules).toEqual([]);
  });

  it('mappe les 9 modules attendus', () => {
    const json = JSON.stringify({
      ssl: { status: 'OK', grade: 'A+' },
      headers: { status: 'WARNING', missing_count: 2 },
      cms: { status: 'OK', cms_detected: 'WordPress' },
    });
    const mods = withScan(json).modules;
    expect(mods.map(m => m.key)).toEqual([
      'ssl',
      'headers',
      'cookies',
      'cors',
      'email',
      'cms',
      'waf',
      'ip',
      'dns',
    ]);
  });

  it('renseigne le detail SSL avec le grade', () => {
    const json = JSON.stringify({ ssl: { status: 'OK', grade: 'A+' } });
    const ssl = withScan(json).modules.find(m => m.key === 'ssl');
    expect(ssl?.detail).toBe('Grade A+');
  });

  it('laisse le detail SSL undefined sans grade', () => {
    const json = JSON.stringify({ ssl: { status: 'OK' } });
    const ssl = withScan(json).modules.find(m => m.key === 'ssl');
    expect(ssl?.detail).toBeUndefined();
  });

  it('renseigne le detail headers avec le nombre de manquants', () => {
    const json = JSON.stringify({ headers: { status: 'WARNING', missing_count: 3 } });
    const h = withScan(json).modules.find(m => m.key === 'headers');
    expect(h?.detail).toBe('3 manquants');
  });

  it('renseigne le detail CMS avec le CMS détecté', () => {
    const json = JSON.stringify({ cms: { status: 'OK', cms_detected: 'Drupal' } });
    const cms = withScan(json).modules.find(m => m.key === 'cms');
    expect(cms?.detail).toBe('Drupal');
  });

  it('propage le statut null quand le module est absent du JSON', () => {
    const waf = withScan('{}').modules.find(m => m.key === 'waf');
    expect(waf?.status).toBeUndefined();
  });
});

describe('ScanGratuitComponent — criticalCount / warningCount', () => {
  function withScan(json: string): ScanGratuitComponent {
    const c = makeComponent();
    (c as any).scan = signal({ results_json: json });
    return c;
  }

  it('compte les modules CRITICAL', () => {
    const json = JSON.stringify({
      ssl: { status: 'CRITICAL' },
      headers: { status: 'CRITICAL' },
      cors: { status: 'OK' },
    });
    expect(withScan(json).criticalCount).toBe(2);
  });

  it('compte les modules WARNING', () => {
    const json = JSON.stringify({
      ssl: { status: 'WARNING' },
      headers: { status: 'OK' },
      cors: { status: 'WARNING' },
    });
    expect(withScan(json).warningCount).toBe(2);
  });

  it('retourne 0 sans scan', () => {
    const c = makeComponent();
    (c as any).scan = signal(null);
    expect(c.criticalCount).toBe(0);
    expect(c.warningCount).toBe(0);
  });
});

describe('ScanGratuitComponent — get score / getGrade / getScoreColor', () => {
  it('retourne null sans résultat', () => {
    const c = makeComponent();
    (c as any).scan = signal(null);
    expect(c.score).toBeNull();
  });

  it('calcule un score à partir du results_json', () => {
    const c = makeComponent();
    (c as any).scan = signal({ results_json: JSON.stringify({ ssl: { status: 'OK' } }) });
    expect(c.score).toBe(100);
  });

  it('délègue getGrade', () => {
    expect(makeComponent().getGrade(95)).toBe('A');
    expect(makeComponent().getGrade(10)).toBe('F');
  });

  it('délègue getScoreColor', () => {
    expect(makeComponent().getScoreColor(95)).toBe('#4ade80');
    expect(makeComponent().getScoreColor(10)).toBe('#f87171');
  });
});

describe('ScanGratuitComponent — get isRunning', () => {
  function withStatus(status: string | null): ScanGratuitComponent {
    const c = makeComponent();
    (c as any).scan = signal(status === null ? null : { status });
    return c;
  }

  it('true pour pending', () => expect(withStatus('pending').isRunning).toBe(true));
  it('true pour running', () => expect(withStatus('running').isRunning).toBe(true));
  it('false pour done', () => expect(withStatus('done').isRunning).toBe(false));
  it('false sans scan', () => expect(withStatus(null).isRunning).toBe(false));
});

describe('ScanGratuitComponent — get urlInvalid', () => {
  function withCtrl(dirty: boolean, invalid: boolean, value: string): ScanGratuitComponent {
    const c = makeComponent();
    (c as any).form = { controls: { url: { dirty, invalid, value } } };
    return c;
  }

  it('true quand dirty + invalid + valeur présente', () => {
    expect(withCtrl(true, true, 'abc').urlInvalid).toBe(true);
  });

  it('false quand non touché', () => {
    expect(withCtrl(false, true, 'abc').urlInvalid).toBe(false);
  });

  it('false quand valide', () => {
    expect(withCtrl(true, false, 'abc').urlInvalid).toBe(false);
  });

  it('false quand valeur vide', () => {
    expect(withCtrl(true, true, '').urlInvalid).toBe(false);
  });
});

describe('ScanGratuitComponent — submit()', () => {
  function makeSubmit(overrides: Partial<Record<string, unknown>> = {}): ScanGratuitComponent {
    const c = makeComponent();
    (c as any).submitting = signal(false);
    (c as any).scan = signal(null);
    (c as any).error = signal(null);
    (c as any).form = {
      controls: { url: { invalid: false } },
      getRawValue: () => ({ url: '  http://x.com  ', email: '', consent: false }),
    };
    (c as any).router = { navigate: vi.fn() };
    (c as any).http = { post: vi.fn().mockReturnValue(of({})) };
    Object.assign(c as any, overrides);
    return c;
  }

  it('ne fait rien si le champ url est invalide', () => {
    const c = makeSubmit();
    (c as any).form.controls.url.invalid = true;
    (c as any).cyberscan = (c as any).billing = { createPublicScan: vi.fn() };
    c.submit();
    expect((c as any).cyberscan.createPublicScan).not.toHaveBeenCalled();
  });

  it('ne fait rien si déjà en cours de soumission', () => {
    const c = makeSubmit();
    (c as any).submitting.set(true);
    (c as any).cyberscan = (c as any).billing = { createPublicScan: vi.fn() };
    c.submit();
    expect((c as any).cyberscan.createPublicScan).not.toHaveBeenCalled();
  });

  it('trim l’URL et navigue vers /demo-result au succès', () => {
    const c = makeSubmit();
    (c as any).cyberscan = (c as any).billing = {
      createPublicScan: vi.fn().mockReturnValue(of({ token: 'tok123' })),
    };
    c.submit();
    expect((c as any).cyberscan.createPublicScan).toHaveBeenCalledWith('http://x.com');
    expect((c as any).router.navigate).toHaveBeenCalledWith(['/demo-result', 'tok123']);
    expect((c as any).submitting()).toBe(false);
  });

  it('abonne à la newsletter si email + consent', () => {
    const c = makeSubmit({
      form: {
        controls: { url: { invalid: false } },
        getRawValue: () => ({ url: 'http://x.com', email: 'a@b.com', consent: true }),
      },
    });
    (c as any).cyberscan = (c as any).billing = {
      createPublicScan: vi.fn().mockReturnValue(of({ token: 'tok' })),
    };
    c.submit();
    expect((c as any).http.post).toHaveBeenCalledWith(
      expect.stringContaining('/newsletter/subscribe'),
      {
        email: 'a@b.com',
      }
    );
  });

  it('n’abonne pas à la newsletter sans consent', () => {
    const c = makeSubmit({
      form: {
        controls: { url: { invalid: false } },
        getRawValue: () => ({ url: 'http://x.com', email: 'a@b.com', consent: false }),
      },
    });
    (c as any).cyberscan = (c as any).billing = {
      createPublicScan: vi.fn().mockReturnValue(of({ token: 'tok' })),
    };
    c.submit();
    expect((c as any).http.post).not.toHaveBeenCalled();
  });

  it('met un message d’erreur en cas d’échec', () => {
    const c = makeSubmit();
    (c as any).cyberscan = (c as any).billing = {
      createPublicScan: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'Boom' } }))),
    };
    c.submit();
    expect((c as any).error()).toBe('Boom');
    expect((c as any).submitting()).toBe(false);
  });

  it('utilise un message par défaut si pas de detail', () => {
    const c = makeSubmit();
    (c as any).cyberscan = (c as any).billing = {
      createPublicScan: vi.fn().mockReturnValue(throwError(() => ({}))),
    };
    c.submit();
    expect((c as any).error()).toContain('Erreur');
  });
});

describe('ScanGratuitComponent — openCheckout()', () => {
  function makeCheckout(authed: boolean): ScanGratuitComponent {
    const c = makeComponent();
    (c as any).auth = { isAuthenticated: () => authed };
    (c as any).router = { navigate: vi.fn() };
    (c as any).checkoutLoading = false;
    return c;
  }

  it('redirige vers l’inscription si non authentifié', () => {
    const c = makeCheckout(false);
    (c as any).cyberscan = (c as any).billing = { getPlans: vi.fn() };
    c.openCheckout();
    expect((c as any).router.navigate).toHaveBeenCalledWith(['/'], {
      queryParams: { action: 'register' },
    });
    expect((c as any).cyberscan.getPlans).not.toHaveBeenCalled();
  });

  it('choisit le plan le moins cher et crée le checkout', () => {
    const c = makeCheckout(true);
    const originalHref = window.location.href;
    const created = vi.fn().mockReturnValue(of({ checkout_url: 'https://pay/x' }));
    (c as any).cyberscan = (c as any).billing = {
      getPlans: vi.fn().mockReturnValue(
        of([
          { id: 1, price_eur: 99 },
          { id: 2, price_eur: 29 },
          { id: 3, price_eur: 59 },
        ])
      ),
      createCheckout: created,
    };
    // window.location.href non testable de façon fiable en jsdom -> on vérifie l'appel createCheckout
    try {
      c.openCheckout();
    } catch {
      /* jsdom peut lever sur navigation */
    }
    expect(created).toHaveBeenCalledWith(2);
    // restaure au cas où
    try {
      window.location.href = originalHref;
    } catch {
      /* ignore */
    }
  });

  it('arrête le chargement si aucun plan', () => {
    const c = makeCheckout(true);
    (c as any).cyberscan = (c as any).billing = { getPlans: vi.fn().mockReturnValue(of([])) };
    c.openCheckout();
    expect((c as any).checkoutLoading).toBe(false);
  });

  it('arrête le chargement en cas d’erreur getPlans', () => {
    const c = makeCheckout(true);
    (c as any).cyberscan = (c as any).billing = {
      getPlans: vi.fn().mockReturnValue(throwError(() => new Error('net'))),
    };
    c.openCheckout();
    expect((c as any).checkoutLoading).toBe(false);
  });
});

describe('ScanGratuitComponent — resetScan()', () => {
  it('réinitialise scan, error et le formulaire', () => {
    const c = makeComponent();
    (c as any).scan = signal({ status: 'done' });
    (c as any).error = signal('oops');
    const reset = vi.fn();
    (c as any).form = { reset };
    (c as any).pollSub = { unsubscribe: vi.fn() };
    c.resetScan();
    expect((c as any).scan()).toBeNull();
    expect((c as any).error()).toBeNull();
    expect(reset).toHaveBeenCalled();
    expect((c as any).pollSub.unsubscribe).toHaveBeenCalled();
  });
});

describe('ScanGratuitComponent — ngOnInit()', () => {
  it('positionne le titre et la meta description', () => {
    const c = makeComponent();
    const setTitle = vi.fn();
    const updateTag = vi.fn();
    (c as any).titleService = { setTitle };
    (c as any).meta = { updateTag };
    c.ngOnInit();
    expect(setTitle).toHaveBeenCalledWith(expect.stringContaining('Scan de sécurité gratuit'));
    expect(updateTag).toHaveBeenCalledWith(expect.objectContaining({ name: 'description' }));
  });
});

describe('ScanGratuitComponent — ngOnDestroy()', () => {
  it('désabonne le polling', () => {
    const c = makeComponent();
    const unsubscribe = vi.fn();
    (c as any).pollSub = { unsubscribe };
    c.ngOnDestroy();
    expect(unsubscribe).toHaveBeenCalled();
  });

  it('ne casse pas sans souscription', () => {
    const c = makeComponent();
    (c as any).pollSub = null;
    expect(() => c.ngOnDestroy()).not.toThrow();
  });
});
