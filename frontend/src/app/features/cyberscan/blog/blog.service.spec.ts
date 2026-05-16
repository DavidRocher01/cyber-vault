import { describe, it, expect } from 'vitest';
import { BlogService } from './blog.service';

function makeService(): BlogService {
  return new BlogService();
}

describe('BlogService — getAll()', () => {
  it('retourne au moins 2 articles', () => {
    expect(makeService().getAll().length).toBeGreaterThanOrEqual(2);
  });

  it('retourne les articles triés du plus récent au plus ancien', () => {
    const articles = makeService().getAll();
    for (let i = 0; i < articles.length - 1; i++) {
      expect(articles[i].date >= articles[i + 1].date).toBe(true);
    }
  });

  it('chaque article possède les champs requis', () => {
    for (const a of makeService().getAll()) {
      expect(a.slug).toBeTruthy();
      expect(a.title).toBeTruthy();
      expect(a.description).toBeTruthy();
      expect(a.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(a.readTime).toBeGreaterThan(0);
      expect(a.htmlContent).toBeTruthy();
      expect(Array.isArray(a.tags)).toBe(true);
    }
  });
});

describe('BlogService — getBySlug()', () => {
  it('retourne l\'article pour un slug existant', () => {
    const a = makeService().getBySlug('audit-cybersecurite-pme-prix-2026');
    expect(a).toBeDefined();
    expect(a!.slug).toBe('audit-cybersecurite-pme-prix-2026');
  });

  it('retourne l\'article e-commerce', () => {
    const a = makeService().getBySlug('vulnerabilites-courantes-sites-ecommerce');
    expect(a).toBeDefined();
    expect(a!.slug).toBe('vulnerabilites-courantes-sites-ecommerce');
  });

  it('retourne undefined pour un slug inconnu', () => {
    expect(makeService().getBySlug('slug-qui-nexiste-pas')).toBeUndefined();
  });

  it('retourne undefined pour une chaîne vide', () => {
    expect(makeService().getBySlug('')).toBeUndefined();
  });
});

describe('BlogService — formatDate()', () => {
  it('formate une date ISO en français', () => {
    const result = makeService().formatDate('2026-05-01');
    expect(result).toContain('2026');
  });

  it('contient le nom du mois en français', () => {
    const result = makeService().formatDate('2026-05-01');
    expect(result).toMatch(/mai/i);
  });

  it('formate une date de janvier', () => {
    const result = makeService().formatDate('2026-01-15');
    expect(result).toContain('2026');
    expect(result).toMatch(/janv/i);
  });
});
