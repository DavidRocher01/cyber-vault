import { describe, it, expect } from 'vitest';
import {
  complianceStatusLabel,
  complianceStatusIcon,
  complianceStatusClass,
  complianceStatusColor,
  complianceScoreColor,
  complianceScoreLabel,
} from './compliance-status.util';

describe('compliance-status.util', () => {
  it('statusLabel mappe les statuts connus + fallback', () => {
    expect(complianceStatusLabel('compliant')).toBe('Conforme');
    expect(complianceStatusLabel('partial')).toBe('Partiel');
    expect(complianceStatusLabel('non_compliant')).toBe('Non conforme');
    expect(complianceStatusLabel('na')).toBe('N/A');
    expect(complianceStatusLabel('???')).toBe('???');
  });

  it('statusIcon/Class/Color ont un fallback pour statut inconnu', () => {
    expect(complianceStatusIcon('compliant')).toBe('check_circle');
    expect(complianceStatusIcon('???')).toBe('help_outline');
    expect(complianceStatusClass('non_compliant')).toContain('text-red-400');
    expect(complianceStatusClass('???')).toContain('text-gray-400');
    expect(complianceStatusColor('partial')).toBe('#facc15');
    expect(complianceStatusColor('???')).toBe('#6b7280');
  });

  it('scoreColor/scoreLabel suivent les seuils 80/50', () => {
    expect(complianceScoreColor(80)).toBe('#4ade80');
    expect(complianceScoreColor(50)).toBe('#facc15');
    expect(complianceScoreColor(49)).toBe('#f87171');
    expect(complianceScoreLabel(80)).toBe('Conforme');
    expect(complianceScoreLabel(50)).toBe('En cours');
    expect(complianceScoreLabel(0)).toBe('Non conforme');
  });
});
