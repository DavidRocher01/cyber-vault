/**
 * QuoteActionComponent — accepte/refuse un devis via token, mappe la réponse vers l'état.
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { of, throwError } from 'rxjs';

async function makeComponent(action: 'accepter' | 'refuser', token = 'tok123') {
  const { QuoteActionComponent } = await import('./quote-action.component');
  const httpMock = { post: vi.fn() };
  const route = {
    snapshot: {
      paramMap: { get: (k: string) => (k === 'token' ? token : null) },
      url: [{ path: action }],
    },
  };
  const injector = Injector.create({
    providers: [
      { provide: ActivatedRoute, useValue: route },
      { provide: HttpClient, useValue: httpMock },
    ],
  });
  const comp = runInInjectionContext(injector, () => new QuoteActionComponent());
  return { comp, httpMock };
}

describe('QuoteActionComponent — endpoint', () => {
  it('accepter -> POST /accept', async () => {
    const { comp, httpMock } = await makeComponent('accepter');
    httpMock.post.mockReturnValue(of({ status: 'accepted', quote_number: 'D-1', already: false }));
    comp.ngOnInit();
    expect(httpMock.post).toHaveBeenCalledWith('/api/v1/quotes/tok123/accept', {});
  });

  it('refuser -> POST /reject', async () => {
    const { comp, httpMock } = await makeComponent('refuser');
    httpMock.post.mockReturnValue(of({ status: 'rejected', quote_number: 'D-1', already: false }));
    comp.ngOnInit();
    expect(httpMock.post).toHaveBeenCalledWith('/api/v1/quotes/tok123/reject', {});
  });
});

describe('QuoteActionComponent — états', () => {
  it('succès -> state = status renvoyé + quoteNumber', async () => {
    const { comp, httpMock } = await makeComponent('accepter');
    httpMock.post.mockReturnValue(of({ status: 'accepted', quote_number: 'D-42', already: false }));
    comp.ngOnInit();
    expect(comp.state()).toBe('accepted');
    expect(comp.quoteNumber()).toBe('D-42');
  });

  it('already=true -> state = already', async () => {
    const { comp, httpMock } = await makeComponent('accepter');
    httpMock.post.mockReturnValue(of({ status: 'accepted', quote_number: 'D-1', already: true }));
    comp.ngOnInit();
    expect(comp.state()).toBe('already');
  });

  it('erreur -> state = error + message', async () => {
    const { comp, httpMock } = await makeComponent('accepter');
    httpMock.post.mockReturnValue(throwError(() => ({ error: { detail: 'Expiré' } })));
    comp.ngOnInit();
    expect(comp.state()).toBe('error');
    expect(comp.errorMsg()).toBe('Expiré');
  });
});
