/**
 * NewsletterUnsubscribeComponent — mappe le query param `status` vers le signal d'état.
 */
import { describe, it, expect } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

async function makeComponent(statusParam: string | null) {
  const { NewsletterUnsubscribeComponent } = await import('./newsletter-unsubscribe.component');
  const route = {
    snapshot: { queryParamMap: { get: (k: string) => (k === 'status' ? statusParam : null) } },
  };
  const injector = Injector.create({
    providers: [{ provide: ActivatedRoute, useValue: route }],
  });
  const comp = runInInjectionContext(injector, () => new NewsletterUnsubscribeComponent());
  return comp;
}

describe('NewsletterUnsubscribeComponent', () => {
  it('status loading au départ (avant ngOnInit)', async () => {
    const comp = await makeComponent('ok');
    expect(comp.status()).toBe('loading');
  });

  it('status=ok quand le param vaut ok', async () => {
    const comp = await makeComponent('ok');
    comp.ngOnInit();
    expect(comp.status()).toBe('ok');
  });

  it('status=invalid quand le param vaut invalid', async () => {
    const comp = await makeComponent('invalid');
    comp.ngOnInit();
    expect(comp.status()).toBe('invalid');
  });

  it('status=loading quand le param est absent', async () => {
    const comp = await makeComponent(null);
    comp.ngOnInit();
    expect(comp.status()).toBe('loading');
  });

  it('status=loading quand le param est inconnu', async () => {
    const comp = await makeComponent('whatever');
    comp.ngOnInit();
    expect(comp.status()).toBe('loading');
  });
});
