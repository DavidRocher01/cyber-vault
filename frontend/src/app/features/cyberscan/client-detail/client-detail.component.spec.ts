import { describe, it, expect } from 'vitest';
import { ClientDetailComponent } from './client-detail.component';

function make(): ClientDetailComponent {
  return Object.create(ClientDetailComponent.prototype) as ClientDetailComponent;
}

// ── docTypeLabel ──────────────────────────────────────────────────────────────

describe('ClientDetailComponent — docTypeLabel()', () => {
  it('retourne "Compte-rendu" pour compte_rendu', () => expect(make().docTypeLabel('compte_rendu')).toBe('Compte-rendu'));
  it('retourne "Rapport" pour rapport', () => expect(make().docTypeLabel('rapport')).toBe('Rapport'));
  it('retourne "Recommandation" pour recommandation', () => expect(make().docTypeLabel('recommandation')).toBe('Recommandation'));
  it('retourne "Contrat" pour contrat', () => expect(make().docTypeLabel('contrat')).toBe('Contrat'));
  it('retourne "Autre" pour autre', () => expect(make().docTypeLabel('autre')).toBe('Autre'));
  it('retourne la valeur brute pour type inconnu', () => expect(make().docTypeLabel('custom')).toBe('custom'));
});

// ── docTypeClass ──────────────────────────────────────────────────────────────

describe('ClientDetailComponent — docTypeClass()', () => {
  it('contient blue pour compte_rendu', () => expect(make().docTypeClass('compte_rendu')).toContain('blue'));
  it('contient cyan pour rapport', () => expect(make().docTypeClass('rapport')).toContain('cyan'));
  it('contient purple pour recommandation', () => expect(make().docTypeClass('recommandation')).toContain('purple'));
  it('retourne classe gray pour type inconnu', () => expect(make().docTypeClass('autre')).toContain('gray'));
});

// ── statusClass ───────────────────────────────────────────────────────────────

describe('ClientDetailComponent — statusClass()', () => {
  it('contient green pour active', () => expect(make().statusClass('active')).toContain('green'));
  it('contient yellow pour inactive', () => expect(make().statusClass('inactive')).toContain('yellow'));
  it('contient red pour churned', () => expect(make().statusClass('churned')).toContain('red'));
  it('retourne gray pour inconnu', () => expect(make().statusClass('other')).toContain('gray'));
});

// ── priorityClass ─────────────────────────────────────────────────────────────

describe('ClientDetailComponent — priorityClass()', () => {
  it('contient red pour critical', () => expect(make().priorityClass('critical')).toContain('red'));
  it('contient orange pour high', () => expect(make().priorityClass('high')).toContain('orange'));
  it('contient yellow pour medium', () => expect(make().priorityClass('medium')).toContain('yellow'));
  it('contient green/blue/gray pour low', () => {
    const cls = make().priorityClass('low');
    expect(cls).toBeDefined();
    expect(cls.length).toBeGreaterThan(0);
  });
});

// ── actionStatusLabel ─────────────────────────────────────────────────────────

describe('ClientDetailComponent — actionStatusLabel()', () => {
  it('retourne "Ouverte" pour open', () => expect(make().actionStatusLabel('open')).toBe('Ouverte'));
  it('retourne "En cours" pour in_progress', () => expect(make().actionStatusLabel('in_progress')).toBe('En cours'));
  it('retourne "Terminée" pour done', () => expect(make().actionStatusLabel('done')).toBe('Terminée'));
  it('retourne "Annulée" pour cancelled', () => expect(make().actionStatusLabel('cancelled')).toBe('Annulée'));
  it('retourne "Reportée" pour postponed', () => expect(make().actionStatusLabel('postponed')).toBe('Reportée'));
  it('retourne la valeur brute pour inconnu', () => expect(make().actionStatusLabel('other')).toBe('other'));
});

// ── visitStatusLabel ──────────────────────────────────────────────────────────

describe('ClientDetailComponent — visitStatusLabel()', () => {
  it('retourne "Planifiée" pour planned', () => expect(make().visitStatusLabel('planned')).toBe('Planifiée'));
  it('retourne "Complétée" pour completed', () => expect(make().visitStatusLabel('completed')).toBe('Complétée'));
  it('retourne "Annulée" pour cancelled', () => expect(make().visitStatusLabel('cancelled')).toBe('Annulée'));
  it('retourne "Reportée" pour postponed', () => expect(make().visitStatusLabel('postponed')).toBe('Reportée'));
  it('retourne valeur brute pour inconnu', () => expect(make().visitStatusLabel('other')).toBe('other'));
});

// ── visitTypeLabel ────────────────────────────────────────────────────────────

describe('ClientDetailComponent — visitTypeLabel()', () => {
  it('retourne "Mensuelle" pour monthly', () => expect(make().visitTypeLabel('monthly')).toBe('Mensuelle'));
  it('retourne "Trimestrielle" pour quarterly', () => expect(make().visitTypeLabel('quarterly')).toBe('Trimestrielle'));
  it('retourne "Annuelle" pour annual', () => expect(make().visitTypeLabel('annual')).toBe('Annuelle'));
  it('retourne "Urgente" pour urgent', () => expect(make().visitTypeLabel('urgent')).toBe('Urgente'));
  it('retourne valeur brute pour inconnu', () => expect(make().visitTypeLabel('other')).toBe('other'));
});

// ── locationLabel ─────────────────────────────────────────────────────────────

describe('ClientDetailComponent — locationLabel()', () => {
  it('retourne "Sur site" pour onsite', () => expect(make().locationLabel('onsite')).toBe('Sur site'));
  it('retourne "À distance" pour remote', () => expect(make().locationLabel('remote')).toBe('À distance'));
  it('retourne "À distance" pour valeur inconnue', () => expect(make().locationLabel('other')).toBe('À distance'));
});

// ── activityLabel ─────────────────────────────────────────────────────────────

describe('ClientDetailComponent — activityLabel()', () => {
  it('retourne le bon libellé pour view_client', () => expect(make().activityLabel('view_client')).toBe('Consultation fiche client'));
  it('retourne le bon libellé pour generate_report', () => expect(make().activityLabel('generate_report')).toBe('Génération de rapport'));
  it('retourne le bon libellé pour create_action', () => expect(make().activityLabel('create_action')).toBe('Création d\'une action'));
  it('retourne la valeur brute pour inconnu', () => expect(make().activityLabel('custom_action')).toBe('custom_action'));
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('ClientDetailComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('retourne une date formatée contenant l\'année', () => {
    const result = make().formatDate('2024-06-15');
    expect(result).toContain('2024');
  });
});

// ── formatAmount ──────────────────────────────────────────────────────────────

describe('ClientDetailComponent — formatAmount()', () => {
  it('retourne "—" pour null', () => expect(make().formatAmount(null)).toBe('—'));
  it('contient € pour un montant valide', () => expect(make().formatAmount(2000)).toContain('€'));
});

// ── visitStatusClass ──────────────────────────────────────────────────────────

describe('ClientDetailComponent — visitStatusClass()', () => {
  it('contient green pour completed', () => expect(make().visitStatusClass('completed')).toContain('green'));
  it('contient red pour cancelled', () => expect(make().visitStatusClass('cancelled')).toContain('red'));
  it('contient yellow pour postponed', () => expect(make().visitStatusClass('postponed')).toContain('yellow'));
  it('contient blue pour planned', () => expect(make().visitStatusClass('planned')).toContain('blue'));
});
