import { describe, it, expect } from 'vitest';
import {
  PhishingStatusBadgeComponent,
  phishingStatusLabel,
  phishingStatusColor,
} from './phishing-status-badge.component';

function makeBadge(status: string): PhishingStatusBadgeComponent {
  const c = Object.create(PhishingStatusBadgeComponent.prototype) as PhishingStatusBadgeComponent;
  (c as { status: string }).status = status;
  return c;
}

describe('phishingStatusLabel()', () => {
  it('retourne Brouillon pour draft', () => expect(phishingStatusLabel('draft')).toBe('Brouillon'));
  it('retourne Vérification domaine pour pending_verification', () =>
    expect(phishingStatusLabel('pending_verification')).toBe('Vérification domaine'));
  it('retourne Prête pour ready', () => expect(phishingStatusLabel('ready')).toBe('Prête'));
  it('retourne Planifiée pour scheduled', () =>
    expect(phishingStatusLabel('scheduled')).toBe('Planifiée'));
  it('retourne Envoi en cours pour sending', () =>
    expect(phishingStatusLabel('sending')).toBe('Envoi en cours'));
  it('retourne En cours pour active', () => expect(phishingStatusLabel('active')).toBe('En cours'));
  it('retourne Terminée pour completed', () =>
    expect(phishingStatusLabel('completed')).toBe('Terminée'));
  it('retourne Annulée pour cancelled', () =>
    expect(phishingStatusLabel('cancelled')).toBe('Annulée'));
  it('retourne la valeur brute pour un statut inconnu', () =>
    expect(phishingStatusLabel('unknown')).toBe('unknown'));
});

describe('phishingStatusColor()', () => {
  it('cyan pour active', () => expect(phishingStatusColor('active')).toContain('cyan'));
  it('cyan pour sending', () => expect(phishingStatusColor('sending')).toContain('cyan'));
  it('green pour completed', () => expect(phishingStatusColor('completed')).toContain('green'));
  it('gray pour draft', () => expect(phishingStatusColor('draft')).toContain('gray'));
  it('blue pour ready', () => expect(phishingStatusColor('ready')).toContain('blue'));
  it('purple pour scheduled', () => expect(phishingStatusColor('scheduled')).toContain('purple'));
  it('red pour cancelled', () => expect(phishingStatusColor('cancelled')).toContain('red'));
  it('yellow par défaut (pending_verification)', () =>
    expect(phishingStatusColor('pending_verification')).toContain('yellow'));
});

describe('PhishingStatusBadgeComponent', () => {
  it('label dérive du statut', () => expect(makeBadge('active').label).toBe('En cours'));
  it('color dérive du statut', () => expect(makeBadge('active').color).toContain('cyan'));
  it('label retombe sur la valeur brute pour un statut inconnu', () =>
    expect(makeBadge('unknown').label).toBe('unknown'));
});
