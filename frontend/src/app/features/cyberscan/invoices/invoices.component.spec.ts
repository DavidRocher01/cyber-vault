import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { InvoicesComponent } from './invoices.component';

function make(): InvoicesComponent {
  const comp = Object.create(InvoicesComponent.prototype) as InvoicesComponent;
  (comp as any).invoices = signal([]);
  (comp as any).loading = signal(true);
  (comp as any).downloading = signal(null);
  return comp;
}

describe('InvoicesComponent — formatAmount()', () => {
  it('convertit les centimes en euros avec €', () => {
    const result = make().formatAmount(9900);
    expect(result).toContain('99');
    expect(result).toContain('€');
  });
  it('formate 0 centimes', () => {
    expect(make().formatAmount(0)).toContain('€');
  });
  it('formate les grands montants', () => {
    const result = make().formatAmount(100000);
    expect(result).toContain('1');
    expect(result).toContain('€');
  });
});

describe('InvoicesComponent — formatDate()', () => {
  it('retourne une date fr-FR', () => {
    const result = make().formatDate('2024-08-15T10:00:00Z');
    expect(result).toContain('2024');
    expect(result).toContain('15');
  });
});

describe('InvoicesComponent — typeLabel()', () => {
  it('Abonnement pour subscription', () => expect(make().typeLabel('subscription')).toBe('Abonnement'));
  it('Audit pour tout autre type', () => expect(make().typeLabel('one_time')).toBe('Audit'));
  it('Audit pour type inconnu', () => expect(make().typeLabel('other')).toBe('Audit'));
});

describe('InvoicesComponent — typeClass()', () => {
  it('contient blue pour subscription', () => expect(make().typeClass('subscription')).toContain('blue'));
  it('contient purple pour tout autre type', () => expect(make().typeClass('one_time')).toContain('purple'));
});
