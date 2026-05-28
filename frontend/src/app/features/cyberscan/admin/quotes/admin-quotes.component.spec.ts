import { describe, it, expect } from 'vitest';
import { AdminQuotesComponent } from './admin-quotes.component';

function make(): AdminQuotesComponent {
  return Object.create(AdminQuotesComponent.prototype) as AdminQuotesComponent;
}

describe('AdminQuotesComponent — formatAmount()', () => {
  it('convertit les centimes en euros avec symbole €', () => {
    const result = make().formatAmount(10000);
    expect(result).toContain('100');
    expect(result).toContain('€');
  });
  it('formate 0 centimes', () => {
    expect(make().formatAmount(0)).toContain('€');
  });
  it('formate 5050 centimes = 50,50 €', () => {
    const result = make().formatAmount(5050);
    expect(result).toContain('50');
    expect(result).toContain('€');
  });
});

describe('AdminQuotesComponent — formatDate()', () => {
  it('retourne une date au format fr-FR', () => {
    const result = make().formatDate('2024-07-20');
    expect(result).toContain('2024');
    expect(result).toContain('20');
  });
});

describe('AdminQuotesComponent — statusLabel()', () => {
  it('Envoyé pour sent', () => expect(make().statusLabel('sent')).toBe('Envoyé'));
  it('Accepté pour accepted', () => expect(make().statusLabel('accepted')).toBe('Accepté'));
  it('Refusé pour rejected', () => expect(make().statusLabel('rejected')).toBe('Refusé'));
  it('Expiré pour expired', () => expect(make().statusLabel('expired')).toBe('Expiré'));
  it('valeur brute pour statut inconnu', () => expect(make().statusLabel('other')).toBe('other'));
});

describe('AdminQuotesComponent — statusClasses()', () => {
  it('contient blue pour sent', () => expect(make().statusClasses('sent')).toContain('blue'));
  it('contient green pour accepted', () => expect(make().statusClasses('accepted')).toContain('green'));
  it('contient red pour rejected', () => expect(make().statusClasses('rejected')).toContain('red'));
  it('contient gray pour expired', () => expect(make().statusClasses('expired')).toContain('gray'));
  it('fallback gray pour inconnu', () => expect(make().statusClasses('other')).toContain('gray'));
});
