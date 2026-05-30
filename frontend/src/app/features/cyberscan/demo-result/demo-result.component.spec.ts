import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { DemoResultComponent } from './demo-result.component';

function make(): DemoResultComponent {
  const comp = Object.create(DemoResultComponent.prototype) as DemoResultComponent;
  (comp as any).scan = signal<any>(null);
  (comp as any).loading = signal(true);
  (comp as any).error = signal<string | null>(null);
  (comp as any).linkCopied = signal(false);
  return comp;
}

function withScan(resultsJson: object, status = 'done') {
  const comp = make();
  (comp as any).scan.set({ status, results_json: JSON.stringify(resultsJson) });
  return comp;
}

describe('DemoResultComponent — targetUrl', () => {
  it('retourne chaîne vide si scan null', () => {
    expect(make().targetUrl).toBe('');
  });
  it("retourne l'URL depuis _meta", () => {
    const comp = withScan({ _meta: { url: 'example.com' } });
    expect(comp.targetUrl).toBe('example.com');
  });
  it('retourne chaîne vide si _meta absent', () => {
    const comp = withScan({ ssl: { status: 'OK' } });
    expect(comp.targetUrl).toBe('');
  });
  it('retourne chaîne vide si results_json null', () => {
    const comp = make();
    (comp as any).scan.set({ status: 'done', results_json: null });
    expect(comp.targetUrl).toBe('');
  });
  it('retourne chaîne vide si JSON invalide', () => {
    const comp = make();
    (comp as any).scan.set({ status: 'done', results_json: 'not-json{' });
    expect(comp.targetUrl).toBe('');
  });
});

describe('DemoResultComponent — isRunning', () => {
  it('retourne false si scan null', () => {
    expect(make().isRunning).toBe(false);
  });
  it('retourne true si status = pending', () => {
    const comp = make();
    (comp as any).scan.set({ status: 'pending' });
    expect(comp.isRunning).toBe(true);
  });
  it('retourne true si status = running', () => {
    const comp = make();
    (comp as any).scan.set({ status: 'running' });
    expect(comp.isRunning).toBe(true);
  });
  it('retourne false si status = done', () => {
    const comp = make();
    (comp as any).scan.set({ status: 'done' });
    expect(comp.isRunning).toBe(false);
  });
  it('retourne false si status = failed', () => {
    const comp = make();
    (comp as any).scan.set({ status: 'failed' });
    expect(comp.isRunning).toBe(false);
  });
});

describe('DemoResultComponent — modules', () => {
  it('retourne tableau vide si scan null', () => {
    expect(make().modules).toHaveLength(0);
  });
  it('retourne tableau vide si results_json null', () => {
    const comp = make();
    (comp as any).scan.set({ status: 'done', results_json: null });
    expect(comp.modules).toHaveLength(0);
  });
  it('retourne tableau vide si JSON invalide', () => {
    const comp = make();
    (comp as any).scan.set({ status: 'done', results_json: 'bad{json' });
    expect(comp.modules).toHaveLength(0);
  });
  it('retourne 9 modules avec un résultat complet', () => {
    const comp = withScan({
      ssl: { status: 'OK', grade: 'A' },
      headers: { status: 'WARNING', missing_count: 2 },
      cookies: { status: 'OK' },
      cors: { status: 'OK' },
      email: { status: 'OK' },
      cms: { status: 'OK', cms_detected: 'WordPress' },
      waf: { status: 'OK', waf_detected: 'Cloudflare' },
      ip: { status: 'OK' },
      dns: { status: 'OK', total_found: 5 },
    });
    expect(comp.modules).toHaveLength(9);
  });
  it('inclut le grade SSL dans le detail', () => {
    const comp = withScan({ ssl: { status: 'OK', grade: 'A+' } });
    const ssl = comp.modules.find(m => m.key === 'ssl');
    expect(ssl?.detail).toContain('A+');
  });
  it('inclut le count de headers manquants dans le detail', () => {
    const comp = withScan({ headers: { status: 'WARNING', missing_count: 3 } });
    const h = comp.modules.find(m => m.key === 'headers');
    expect(h?.detail).toContain('3');
  });
  it('inclut le CMS détecté dans le detail', () => {
    const comp = withScan({ cms: { status: 'OK', cms_detected: 'Drupal' } });
    const cms = comp.modules.find(m => m.key === 'cms');
    expect(cms?.detail).toBe('Drupal');
  });
  it('statut null si la clé est absente du JSON', () => {
    const comp = withScan({});
    const ssl = comp.modules.find(m => m.key === 'ssl');
    expect(ssl?.status).toBeUndefined();
  });
});

describe('DemoResultComponent — moduleIcon()', () => {
  it('check_circle pour OK', () => expect(make().moduleIcon('OK')).toBe('check_circle'));
  it('warning pour WARNING', () => expect(make().moduleIcon('WARNING')).toBe('warning'));
  it('cancel pour CRITICAL', () => expect(make().moduleIcon('CRITICAL')).toBe('cancel'));
  it('help_outline par défaut', () => expect(make().moduleIcon(null)).toBe('help_outline'));
  it('help_outline pour inconnu', () => expect(make().moduleIcon('UNKNOWN')).toBe('help_outline'));
});

describe('DemoResultComponent — moduleColor()', () => {
  it('text-green-400 pour OK', () => expect(make().moduleColor('OK')).toBe('text-green-400'));
  it('text-yellow-400 pour WARNING', () =>
    expect(make().moduleColor('WARNING')).toBe('text-yellow-400'));
  it('text-red-400 pour CRITICAL', () =>
    expect(make().moduleColor('CRITICAL')).toBe('text-red-400'));
  it('text-gray-500 par défaut', () => expect(make().moduleColor(null)).toBe('text-gray-500'));
  it('text-gray-500 pour inconnu', () => expect(make().moduleColor('OTHER')).toBe('text-gray-500'));
});
