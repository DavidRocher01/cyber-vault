/**
 * UrlScannerComponent — tests des méthodes utilitaires pures.
 */
import { describe, it, expect } from 'vitest';
import { UrlScannerComponent } from './url-scanner.component';

function make(): UrlScannerComponent {
  return Object.create(UrlScannerComponent.prototype) as UrlScannerComponent;
}

describe('UrlScannerComponent — verdictColor()', () => {
  it('retourne vert pour safe', () => expect(make().verdictColor('safe')).toContain('green'));
  it('retourne jaune pour suspicious', () => expect(make().verdictColor('suspicious')).toContain('yellow'));
  it('retourne rouge pour malicious', () => expect(make().verdictColor('malicious')).toContain('red'));
  it('retourne gris pour null', () => expect(make().verdictColor(null)).toContain('gray'));
  it('retourne gris pour inconnu', () => expect(make().verdictColor('unknown')).toContain('gray'));
});

describe('UrlScannerComponent — verdictBg()', () => {
  it('retourne bg vert pour safe', () => expect(make().verdictBg('safe')).toContain('green'));
  it('retourne bg jaune pour suspicious', () => expect(make().verdictBg('suspicious')).toContain('yellow'));
  it('retourne bg rouge pour malicious', () => expect(make().verdictBg('malicious')).toContain('red'));
  it('retourne bg gris pour null', () => expect(make().verdictBg(null)).toContain('gray'));
});

describe('UrlScannerComponent — verdictLabel()', () => {
  it('traduit safe → Sûr', () => expect(make().verdictLabel('safe')).toBe('Sûr'));
  it('traduit suspicious → Suspect', () => expect(make().verdictLabel('suspicious')).toBe('Suspect'));
  it('traduit malicious → Malveillant', () => expect(make().verdictLabel('malicious')).toBe('Malveillant'));
  it('retourne "—" pour null', () => expect(make().verdictLabel(null)).toBe('—'));
});

describe('UrlScannerComponent — verdictIcon()', () => {
  it('retourne verified_user pour safe', () => expect(make().verdictIcon('safe')).toBe('verified_user'));
  it('retourne warning pour suspicious', () => expect(make().verdictIcon('suspicious')).toBe('warning'));
  it('retourne gpp_bad pour malicious', () => expect(make().verdictIcon('malicious')).toBe('gpp_bad'));
  it('retourne help_outline pour null', () => expect(make().verdictIcon(null)).toBe('help_outline'));
});

describe('UrlScannerComponent — threatTypeLabel()', () => {
  it('traduit phishing', () => expect(make().threatTypeLabel('phishing')).toBe('Phishing'));
  it('traduit malware', () => expect(make().threatTypeLabel('malware')).toBe('Malware'));
  it('traduit redirect', () => expect(make().threatTypeLabel('redirect')).toBe('Redirection suspecte'));
  it('traduit tracker', () => expect(make().threatTypeLabel('tracker')).toBe('Tracker'));
  it('traduit malicious_domain', () => expect(make().threatTypeLabel('malicious_domain')).toBe('Domaine malveillant'));
  it('retourne la valeur brute pour un type inconnu', () => expect(make().threatTypeLabel('custom_type')).toBe('custom_type'));
  it('retourne "—" pour null', () => expect(make().threatTypeLabel(null)).toBe('—'));
});

describe('UrlScannerComponent — severityColor()', () => {
  it('retourne les classes pour critical', () => expect(make().severityColor('critical')).toContain('red'));
  it('retourne les classes pour high', () => expect(make().severityColor('high')).toContain('orange'));
  it('retourne les classes pour medium', () => expect(make().severityColor('medium')).toContain('yellow'));
  it('retourne les classes par défaut pour low', () => expect(make().severityColor('low')).toContain('gray'));
});

describe('UrlScannerComponent — severityLabel()', () => {
  it('traduit critical → Critique', () => expect(make().severityLabel('critical')).toBe('Critique'));
  it('traduit high → Élevé', () => expect(make().severityLabel('high')).toBe('Élevé'));
  it('traduit low → Faible', () => expect(make().severityLabel('low')).toBe('Faible'));
  it('retourne la valeur brute si inconnue', () => expect(make().severityLabel('exotic')).toBe('exotic'));
});

describe('UrlScannerComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('formate une date ISO', () => {
    const result = make().formatDate('2024-01-15T10:00:00Z');
    expect(result).toContain('2024');
  });
});

describe('UrlScannerComponent — scoreGradient()', () => {
  it('retourne rouge (#f87171) pour score >= 66', () => {
    expect(make().scoreGradient(80)).toBe('#f87171');
    expect(make().scoreGradient(66)).toBe('#f87171');
  });

  it('retourne jaune (#facc15) pour score entre 31 et 65', () => {
    expect(make().scoreGradient(50)).toBe('#facc15');
    expect(make().scoreGradient(31)).toBe('#facc15');
  });

  it('retourne vert (#4ade80) pour score <= 30', () => {
    expect(make().scoreGradient(0)).toBe('#4ade80');
    expect(make().scoreGradient(30)).toBe('#4ade80');
  });
});
