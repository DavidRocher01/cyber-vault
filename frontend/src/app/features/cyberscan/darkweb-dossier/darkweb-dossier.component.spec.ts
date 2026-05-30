import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { DarkwebDossierComponent } from './darkweb-dossier.component';

function make(): DarkwebDossierComponent {
  const comp = Object.create(DarkwebDossierComponent.prototype) as DarkwebDossierComponent;
  (comp as any).dossiers = signal([]);
  (comp as any).loading = signal(false);
  return comp;
}

describe('DarkwebDossierComponent — riskColor()', () => {
  it('text-gray-500 pour null', () => expect(make().riskColor(null)).toBe('text-gray-500'));
  it('text-red-400 si score ≥ 50', () => expect(make().riskColor(50)).toBe('text-red-400'));
  it('text-red-400 si score = 100', () => expect(make().riskColor(100)).toBe('text-red-400'));
  it('text-yellow-400 si score entre 20 et 49', () =>
    expect(make().riskColor(30)).toBe('text-yellow-400'));
  it('text-yellow-400 si score = 20', () => expect(make().riskColor(20)).toBe('text-yellow-400'));
  it('text-green-400 si score < 20', () => expect(make().riskColor(10)).toBe('text-green-400'));
  it('text-green-400 si score = 0', () => expect(make().riskColor(0)).toBe('text-green-400'));
});

describe('DarkwebDossierComponent — riskBg()', () => {
  it('gray pour null', () => expect(make().riskBg(null)).toContain('gray'));
  it('red pour score ≥ 50', () => expect(make().riskBg(75)).toContain('red'));
  it('yellow pour score entre 20 et 49', () => expect(make().riskBg(25)).toContain('yellow'));
  it('green pour score < 20', () => expect(make().riskBg(5)).toContain('green'));
});

describe('DarkwebDossierComponent — riskLabel()', () => {
  it('— pour null', () => expect(make().riskLabel(null)).toBe('—'));
  it('Risque élevé si score ≥ 50', () => expect(make().riskLabel(60)).toBe('Risque élevé'));
  it('Risque modéré si score entre 20 et 49', () =>
    expect(make().riskLabel(35)).toBe('Risque modéré'));
  it('Risque faible si score < 20', () => expect(make().riskLabel(0)).toBe('Risque faible'));
});

describe('DarkwebDossierComponent — statusLabel()', () => {
  it('En attente pour pending', () => expect(make().statusLabel('pending')).toBe('En attente'));
  it('Analyse en cours pour processing', () =>
    expect(make().statusLabel('processing')).toBe('Analyse en cours'));
  it('Terminé pour completed', () => expect(make().statusLabel('completed')).toBe('Terminé'));
  it('Erreur pour failed', () => expect(make().statusLabel('failed')).toBe('Erreur'));
  it('valeur brute pour statut inconnu', () => expect(make().statusLabel('other')).toBe('other'));
});

describe('DarkwebDossierComponent — statusColor()', () => {
  it('contient green pour completed', () =>
    expect(make().statusColor('completed')).toContain('green'));
  it('contient cyan pour processing', () =>
    expect(make().statusColor('processing')).toContain('cyan'));
  it('contient red pour failed', () => expect(make().statusColor('failed')).toContain('red'));
  it('contient gray par défaut', () => expect(make().statusColor('pending')).toContain('gray'));
});

describe('DarkwebDossierComponent — formatDate()', () => {
  it('retourne — pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("contient l'année pour une date valide", () => {
    expect(make().formatDate('2024-05-20T10:00:00Z')).toContain('2024');
  });
  it('contient le jour', () => {
    expect(make().formatDate('2024-05-20T10:00:00Z')).toContain('20');
  });
});
