import { describe, it, expect } from 'vitest';
import { ConsultantDashboardComponent } from './consultant-dashboard.component';

function make(): ConsultantDashboardComponent {
  return Object.create(ConsultantDashboardComponent.prototype) as ConsultantDashboardComponent;
}

// ── formulaLabel ──────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — formulaLabel()', () => {
  it('retourne "Essentiel" pour essentiel', () =>
    expect(make().formulaLabel('essentiel')).toBe('Essentiel'));
  it('retourne "Premium" pour premium', () =>
    expect(make().formulaLabel('premium')).toBe('Premium'));
  it('retourne "Excellence" pour excellence', () =>
    expect(make().formulaLabel('excellence')).toBe('Excellence'));
  it('retourne "—" pour null', () => expect(make().formulaLabel(null)).toBe('—'));
  it('retourne "—" pour valeur inconnue', () => expect(make().formulaLabel('unknown')).toBe('—'));
});

// ── formulaClass ──────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — formulaClass()', () => {
  it('contient blue pour essentiel', () =>
    expect(make().formulaClass('essentiel')).toContain('blue'));
  it('contient purple pour premium', () =>
    expect(make().formulaClass('premium')).toContain('purple'));
  it('contient amber pour excellence', () =>
    expect(make().formulaClass('excellence')).toContain('amber'));
  it('retourne classe gray pour null', () => expect(make().formulaClass(null)).toContain('gray'));
});

// ── clientStatusClass ─────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — clientStatusClass()', () => {
  it('contient green pour active', () =>
    expect(make().clientStatusClass('active')).toContain('green'));
  it('contient yellow pour inactive', () =>
    expect(make().clientStatusClass('inactive')).toContain('yellow'));
  it('contient red pour churned', () =>
    expect(make().clientStatusClass('churned')).toContain('red'));
  it('retourne classe gray pour inconnu', () =>
    expect(make().clientStatusClass('other')).toContain('gray'));
});

// ── statusColor ───────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — statusColor()', () => {
  it('contient green pour OK', () => expect(make().statusColor('OK')).toContain('green'));
  it('contient yellow pour WARNING', () =>
    expect(make().statusColor('WARNING')).toContain('yellow'));
  it('contient red pour CRITICAL', () => expect(make().statusColor('CRITICAL')).toContain('red'));
  it('retourne classe gray pour null', () => expect(make().statusColor(null)).toContain('gray'));
});

// ── statusIcon ────────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — statusIcon()', () => {
  it('retourne verified_user pour OK', () => expect(make().statusIcon('OK')).toBe('verified_user'));
  it('retourne warning pour WARNING', () => expect(make().statusIcon('WARNING')).toBe('warning'));
  it('retourne gpp_bad pour CRITICAL', () => expect(make().statusIcon('CRITICAL')).toBe('gpp_bad'));
  it('retourne help_outline pour null', () => expect(make().statusIcon(null)).toBe('help_outline'));
});

// ── alertSeverityClass ────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — alertSeverityClass()', () => {
  it('contient red pour critical', () =>
    expect(make().alertSeverityClass('critical')).toContain('red'));
  it('contient orange pour high', () =>
    expect(make().alertSeverityClass('high')).toContain('orange'));
  it('contient yellow pour medium', () =>
    expect(make().alertSeverityClass('medium')).toContain('yellow'));
});

// ── alertIconColor ────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — alertIconColor()', () => {
  it('contient red pour critical', () =>
    expect(make().alertIconColor('critical')).toContain('red'));
  it('contient orange pour high', () => expect(make().alertIconColor('high')).toContain('orange'));
  it('contient yellow pour medium', () =>
    expect(make().alertIconColor('medium')).toContain('yellow'));
});

// ── suggestionIcon ────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — suggestionIcon()', () => {
  it('retourne trending_up pour upsell_opportunity', () =>
    expect(make().suggestionIcon('upsell_opportunity')).toBe('trending_up'));
  it('retourne notification_important pour engagement_alert', () =>
    expect(make().suggestionIcon('engagement_alert')).toBe('notification_important'));
  it('retourne event_available pour renewal_upcoming', () =>
    expect(make().suggestionIcon('renewal_upcoming')).toBe('event_available'));
  it('retourne assignment_late pour high_overdue', () =>
    expect(make().suggestionIcon('high_overdue')).toBe('assignment_late'));
  it('retourne lightbulb pour type inconnu', () =>
    expect(make().suggestionIcon('other')).toBe('lightbulb'));
});

// ── visitTypeLabel ────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — visitTypeLabel()', () => {
  it('retourne "Mensuelle" pour monthly', () =>
    expect(make().visitTypeLabel('monthly')).toBe('Mensuelle'));
  it('retourne "Trimestrielle" pour quarterly', () =>
    expect(make().visitTypeLabel('quarterly')).toBe('Trimestrielle'));
  it('retourne "Annuelle" pour annual', () =>
    expect(make().visitTypeLabel('annual')).toBe('Annuelle'));
  it('retourne "Urgente" pour urgent', () =>
    expect(make().visitTypeLabel('urgent')).toBe('Urgente'));
  it('retourne la valeur brute pour inconnu', () =>
    expect(make().visitTypeLabel('other')).toBe('other'));
});

// ── locationLabel ─────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — locationLabel()', () => {
  it('retourne "Sur site" pour onsite', () =>
    expect(make().locationLabel('onsite')).toBe('Sur site'));
  it('retourne "À distance" pour remote', () =>
    expect(make().locationLabel('remote')).toBe('À distance'));
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("retourne une date contenant l'année", () => {
    const result = make().formatDate('2024-03-15T10:00:00Z');
    expect(result).toContain('2024');
  });
});

// ── formatAmount ──────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — formatAmount()', () => {
  it('retourne "—" pour null', () => expect(make().formatAmount(null)).toBe('—'));
  it('contient € pour un montant valide', () => expect(make().formatAmount(1500)).toContain('€'));
  it('contient 1 500 pour 1500', () => expect(make().formatAmount(1500)).toContain('500'));
});
