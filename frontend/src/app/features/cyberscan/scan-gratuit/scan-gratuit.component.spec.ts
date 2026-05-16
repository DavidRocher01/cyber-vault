import { describe, it, expect } from 'vitest';
import { ScanGratuitComponent } from './scan-gratuit.component';

function makeComponent(): ScanGratuitComponent {
  return Object.create(ScanGratuitComponent.prototype) as ScanGratuitComponent;
}

describe('ScanGratuitComponent — moduleIcon()', () => {
  it('retourne check_circle pour OK', () => {
    expect(makeComponent().moduleIcon('OK')).toBe('check_circle');
  });

  it('retourne warning pour WARNING', () => {
    expect(makeComponent().moduleIcon('WARNING')).toBe('warning');
  });

  it('retourne cancel pour CRITICAL', () => {
    expect(makeComponent().moduleIcon('CRITICAL')).toBe('cancel');
  });

  it('retourne help_outline pour null', () => {
    expect(makeComponent().moduleIcon(null)).toBe('help_outline');
  });

  it('retourne help_outline pour statut inconnu', () => {
    expect(makeComponent().moduleIcon('UNKNOWN')).toBe('help_outline');
  });
});

describe('ScanGratuitComponent — moduleColor()', () => {
  it('retourne green pour OK', () => {
    expect(makeComponent().moduleColor('OK')).toContain('green');
  });

  it('retourne yellow pour WARNING', () => {
    expect(makeComponent().moduleColor('WARNING')).toContain('yellow');
  });

  it('retourne red pour CRITICAL', () => {
    expect(makeComponent().moduleColor('CRITICAL')).toContain('red');
  });

  it('retourne gray pour null', () => {
    expect(makeComponent().moduleColor(null)).toContain('gray');
  });

  it('retourne gray pour statut inconnu', () => {
    expect(makeComponent().moduleColor('UNKNOWN')).toContain('gray');
  });
});
