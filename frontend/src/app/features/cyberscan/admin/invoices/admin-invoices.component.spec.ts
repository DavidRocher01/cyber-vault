import { describe, it, expect } from 'vitest';
import { AdminInvoicesComponent } from './admin-invoices.component';

function make(): AdminInvoicesComponent {
  return Object.create(AdminInvoicesComponent.prototype) as AdminInvoicesComponent;
}

describe('AdminInvoicesComponent — formatAmount()', () => {
  it('convertit les centimes en euros avec symbole €', () => {
    const result = make().formatAmount(25000);
    expect(result).toContain('250');
    expect(result).toContain('€');
  });
  it('formate 0 centimes', () => {
    expect(make().formatAmount(0)).toContain('€');
  });
  it('formate les grands montants', () => {
    const result = make().formatAmount(1_000_000);
    expect(result).toContain('€');
  });
});

describe('AdminInvoicesComponent — formatDate()', () => {
  it('retourne une date au format fr-FR', () => {
    const result = make().formatDate('2024-09-05');
    expect(result).toContain('2024');
    expect(result).toContain('05');
  });
  it('formate une date ISO complète', () => {
    const result = make().formatDate('2024-01-15T10:30:00Z');
    expect(result).toContain('2024');
  });
});
