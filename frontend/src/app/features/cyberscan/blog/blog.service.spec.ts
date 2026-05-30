import { describe, it, expect, vi } from 'vitest';
import { of, throwError } from 'rxjs';
import { BlogService, FALLBACK_ARTICLES } from './blog.service';

function makeService(httpGet?: (url: string) => any) {
  const http = {
    get: vi.fn().mockImplementation(httpGet ?? (() => of([]))),
  };
  const service = Object.create(BlogService.prototype) as BlogService;
  (service as any).http = http;
  return { service, http };
}

describe('BlogService — getAll()', () => {
  it('appelle GET /api/v1/blog/articles', () => {
    const { service, http } = makeService(() => of([]));
    service.getAll().subscribe();
    expect(http.get).toHaveBeenCalledWith('/api/v1/blog/articles');
  });

  it('retourne les articles triés du plus récent au plus ancien', () => {
    const articles = [
      { slug: 'old', date: '2026-01-01', readTime: 5, tags: [] },
      { slug: 'new', date: '2026-05-12', readTime: 5, tags: [] },
    ];
    const { service } = makeService(() => of(articles));
    let result: any[] = [];
    service.getAll().subscribe(r => (result = r));
    expect(result[0].slug).toBe('new');
    expect(result[1].slug).toBe('old');
  });

  it("retourne le fallback trié si l'API échoue", () => {
    const { service } = makeService(() => throwError(() => new Error('network')));
    let result: any[] = [];
    service.getAll().subscribe(r => (result = r));
    expect(result.length).toBeGreaterThanOrEqual(2);
    for (let i = 0; i < result.length - 1; i++) {
      expect(result[i].date >= result[i + 1].date).toBe(true);
    }
  });

  it('il y a au moins 2 articles de fallback', () => {
    expect(FALLBACK_ARTICLES.length).toBeGreaterThanOrEqual(2);
  });

  it('chaque article de fallback possède les champs requis', () => {
    for (const a of FALLBACK_ARTICLES) {
      expect(a.slug).toBeTruthy();
      expect(a.title).toBeTruthy();
      expect(a.description).toBeTruthy();
      expect(a.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(a.readTime).toBeGreaterThan(0);
      expect(Array.isArray(a.tags)).toBe(true);
    }
  });
});

describe('BlogService — getBySlug()', () => {
  it('appelle GET /api/v1/blog/articles/{slug}', () => {
    const article = {
      slug: 'my-article',
      title: 'Test',
      date: '2026-05-01',
      readTime: 5,
      tags: [],
      htmlContent: '<p/>',
    };
    const { service, http } = makeService(() => of(article));
    let result: any;
    service.getBySlug('my-article').subscribe(r => (result = r));
    expect(http.get).toHaveBeenCalledWith('/api/v1/blog/articles/my-article');
    expect(result?.slug).toBe('my-article');
  });

  it("retourne le fallback si l'API échoue et le slug existe", () => {
    const { service } = makeService(() => throwError(() => new Error('fail')));
    let result: any;
    service.getBySlug('audit-cybersecurite-pme-prix-2026').subscribe(r => (result = r));
    expect(result?.slug).toBe('audit-cybersecurite-pme-prix-2026');
  });

  it("retourne null si l'API échoue et le slug est inconnu", () => {
    const { service } = makeService(() => throwError(() => new Error('fail')));
    let result: any = 'not-set';
    service.getBySlug('slug-qui-nexiste-pas').subscribe(r => (result = r));
    expect(result).toBeNull();
  });
});

describe('BlogService — formatDate()', () => {
  it('formate une date ISO en français', () => {
    const { service } = makeService();
    expect(service.formatDate('2026-05-01')).toContain('2026');
  });

  it('contient le nom du mois en français', () => {
    const { service } = makeService();
    expect(service.formatDate('2026-05-01')).toMatch(/mai/i);
  });

  it('formate une date de janvier', () => {
    const { service } = makeService();
    const result = service.formatDate('2026-01-15');
    expect(result).toContain('2026');
    expect(result).toMatch(/janv/i);
  });
});
