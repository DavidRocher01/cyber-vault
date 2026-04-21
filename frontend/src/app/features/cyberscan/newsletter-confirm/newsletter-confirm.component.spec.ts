import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError, NEVER } from 'rxjs';
import { NewsletterConfirmComponent } from './newsletter-confirm.component';

function make(params: Record<string, string> = {}) {
  const comp = Object.create(NewsletterConfirmComponent.prototype) as NewsletterConfirmComponent;
  (comp as any).status = signal<'loading' | 'ok' | 'invalid'>('loading');
  (comp as any).route = {
    snapshot: { queryParamMap: { get: (k: string) => params[k] ?? null } },
  };
  return comp;
}

describe('NewsletterConfirmComponent — ngOnInit avec ?status', () => {
  it('passe à "ok" si ?status=ok', () => {
    const comp = make({ status: 'ok' });
    (comp as any).http = { get: vi.fn() };
    comp.ngOnInit();
    expect(comp.status()).toBe('ok');
    expect((comp as any).http.get).not.toHaveBeenCalled();
  });

  it('passe à "invalid" si ?status=invalid', () => {
    const comp = make({ status: 'invalid' });
    (comp as any).http = { get: vi.fn() };
    comp.ngOnInit();
    expect(comp.status()).toBe('invalid');
    expect((comp as any).http.get).not.toHaveBeenCalled();
  });
});

describe('NewsletterConfirmComponent — ngOnInit sans token', () => {
  it('passe à "invalid" si aucun token ni status', () => {
    const comp = make({});
    (comp as any).http = { get: vi.fn() };
    comp.ngOnInit();
    expect(comp.status()).toBe('invalid');
    expect((comp as any).http.get).not.toHaveBeenCalled();
  });
});

describe('NewsletterConfirmComponent — ngOnInit avec ?token', () => {
  it('reste "loading" pendant la requête', () => {
    const comp = make({ token: 'abc' });
    (comp as any).http = { get: vi.fn().mockReturnValue(NEVER) };
    comp.ngOnInit();
    expect(comp.status()).toBe('loading');
  });

  it('passe à "ok" si le backend répond avec succès', () => {
    const comp = make({ token: 'valid-token' });
    (comp as any).http = { get: vi.fn().mockReturnValue(of({ status: 200 })) };
    comp.ngOnInit();
    expect(comp.status()).toBe('ok');
  });

  it('passe à "invalid" si le backend retourne une erreur', () => {
    const comp = make({ token: 'bad-token' });
    (comp as any).http = { get: vi.fn().mockReturnValue(throwError(() => new Error('404'))) };
    comp.ngOnInit();
    expect(comp.status()).toBe('invalid');
  });

  it('appelle le bon endpoint avec le token', () => {
    const comp = make({ token: 'mytoken' });
    const getSpy = vi.fn().mockReturnValue(of({}));
    (comp as any).http = { get: getSpy };
    comp.ngOnInit();
    expect(getSpy).toHaveBeenCalledOnce();
    const [url, options] = getSpy.mock.calls[0];
    expect(url).toContain('/newsletter/confirm');
    expect(options.params).toMatchObject({ token: 'mytoken' });
  });
});
