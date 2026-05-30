import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { SubdomainsComponent } from './subdomains.component';
import type { SubdomainEntry, SubdomainResult } from '../services/cyberscan.service';

function make(): SubdomainsComponent {
  const comp = Object.create(SubdomainsComponent.prototype) as SubdomainsComponent;
  (comp as any).siteId = signal(0);
  (comp as any).result = signal<SubdomainResult | null>(null);
  (comp as any).loading = signal(true);
  (comp as any).error = signal(null);
  (comp as any).search = signal('');
  return comp;
}

function entry(subdomain: string, ip = '1.2.3.4'): SubdomainEntry {
  return { subdomain, ip, port: 443, is_https: true, resolved: true } as any;
}

function makeResult(entries: SubdomainEntry[]): SubdomainResult {
  return { total: entries.length, subdomains: entries } as any;
}

describe('SubdomainsComponent — formatDate()', () => {
  it('retourne — pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("contient l'année pour une date valide", () => {
    expect(make().formatDate('2024-07-10T12:00:00Z')).toContain('2024');
  });
  it('contient le jour', () => {
    expect(make().formatDate('2024-07-10T12:00:00Z')).toContain('10');
  });
});

describe('SubdomainsComponent — filtered getter', () => {
  it('retourne tout sans filtre', () => {
    const comp = make();
    (comp as any).result.set(makeResult([entry('api.example.com'), entry('mail.example.com')]));
    expect(comp.filtered.length).toBe(2);
  });

  it('retourne tableau vide si result est null', () => {
    expect(make().filtered).toHaveLength(0);
  });

  it('filtre par sous-domaine (insensible à la casse)', () => {
    const comp = make();
    (comp as any).result.set(makeResult([entry('api.example.com'), entry('mail.example.com')]));
    (comp as any).search.set('API');
    expect(comp.filtered.length).toBe(1);
    expect(comp.filtered[0].subdomain).toBe('api.example.com');
  });

  it('filtre par IP', () => {
    const comp = make();
    (comp as any).result.set(
      makeResult([entry('api.example.com', '10.0.0.1'), entry('mail.example.com', '10.0.0.2')])
    );
    (comp as any).search.set('10.0.0.1');
    expect(comp.filtered.length).toBe(1);
  });

  it('retourne vide si aucun résultat', () => {
    const comp = make();
    (comp as any).result.set(makeResult([entry('api.example.com')]));
    (comp as any).search.set('zzz');
    expect(comp.filtered.length).toBe(0);
  });
});
