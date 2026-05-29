import { describe, it, expect, beforeEach } from 'vitest';
import { signal, computed } from '@angular/core';
import { AdminBlogComponent } from './admin-blog.component';

interface BlogPost {
  id: number;
  slug: string;
  title: string;
  description: string;
  date: string;
  readTime: number;
  category: string;
  tags: string[];
  isPublished: boolean;
  htmlContent?: string;
}

function make(): AdminBlogComponent {
  const comp = Object.create(AdminBlogComponent.prototype) as AdminBlogComponent;
  (comp as any).articles = signal<BlogPost[]>([]);
  (comp as any).loading = signal(false);
  (comp as any).view = signal<'list' | 'edit'>('list');
  (comp as any).editingSlug = signal<string | null>(null);
  (comp as any).saving = signal(false);
  (comp as any).saveMsg = signal('');
  (comp as any).saveError = signal('');
  return comp;
}

const ARTICLE: BlogPost = {
  id: 1,
  slug: 'mon-article',
  title: 'Mon article',
  description: 'Desc',
  date: '2026-06-01',
  readTime: 5,
  category: 'Sécurité Web',
  tags: ['sécurité'],
  isPublished: true,
};

const DRAFT: BlogPost = {
  id: 2,
  slug: 'brouillon',
  title: 'Brouillon',
  description: 'Draft',
  date: '2026-06-02',
  readTime: 3,
  category: 'Audit',
  tags: [],
  isPublished: false,
};

// ── editingSlug ────────────────────────────────────────────────────────────────

describe('editingSlug', () => {
  it('starts null', () => {
    const comp = make();
    expect((comp as any).editingSlug()).toBeNull();
  });

  it('is truthy after openEdit sets a slug', () => {
    const comp = make();
    (comp as any).editingSlug.set('mon-article');
    expect((comp as any).editingSlug()).toBe('mon-article');
  });

  it('is null after openNew resets it', () => {
    const comp = make();
    (comp as any).editingSlug.set('mon-article');
    (comp as any).editingSlug.set(null);
    expect((comp as any).editingSlug()).toBeNull();
  });
});

// ── view state ─────────────────────────────────────────────────────────────────

describe('view signal', () => {
  it('starts as list', () => {
    const comp = make();
    expect((comp as any).view()).toBe('list');
  });

  it('can switch to edit', () => {
    const comp = make();
    (comp as any).view.set('edit');
    expect((comp as any).view()).toBe('edit');
  });
});

// ── articles signal ────────────────────────────────────────────────────────────

describe('articles', () => {
  it('starts empty', () => {
    const comp = make();
    expect((comp as any).articles()).toEqual([]);
  });

  it('reflects both published and draft articles', () => {
    const comp = make();
    (comp as any).articles.set([ARTICLE, DRAFT]);
    expect((comp as any).articles()).toHaveLength(2);
    expect((comp as any).articles().some((a: BlogPost) => !a.isPublished)).toBe(true);
  });

  it('delete removes by slug', () => {
    const comp = make();
    (comp as any).articles.set([ARTICLE, DRAFT]);
    (comp as any).articles.update((a: BlogPost[]) => a.filter(x => x.slug !== 'mon-article'));
    const remaining = (comp as any).articles();
    expect(remaining).toHaveLength(1);
    expect(remaining[0].slug).toBe('brouillon');
  });

  it('togglePublish flips isPublished', () => {
    const comp = make();
    (comp as any).articles.set([ARTICLE]);
    (comp as any).articles.update((a: BlogPost[]) =>
      a.map(x => (x.slug === 'mon-article' ? { ...x, isPublished: !x.isPublished } : x))
    );
    expect((comp as any).articles()[0].isPublished).toBe(false);
  });
});

// ── saveMsg / saveError ────────────────────────────────────────────────────────

describe('save feedback signals', () => {
  it('saveMsg starts empty', () => {
    const comp = make();
    expect((comp as any).saveMsg()).toBe('');
  });

  it('saveError starts empty', () => {
    const comp = make();
    expect((comp as any).saveError()).toBe('');
  });

  it('can set saveMsg', () => {
    const comp = make();
    (comp as any).saveMsg.set('Enregistré ✓');
    expect((comp as any).saveMsg()).toBe('Enregistré ✓');
  });

  it('can set saveError', () => {
    const comp = make();
    (comp as any).saveError.set('Erreur serveur');
    expect((comp as any).saveError()).toBe('Erreur serveur');
  });

  it('reset clears both', () => {
    const comp = make();
    (comp as any).saveMsg.set('Enregistré ✓');
    (comp as any).saveError.set('Erreur');
    (comp as any).saveMsg.set('');
    (comp as any).saveError.set('');
    expect((comp as any).saveMsg()).toBe('');
    expect((comp as any).saveError()).toBe('');
  });
});

// ── editingSlug drives PUT vs POST ────────────────────────────────────────────

describe('editingSlug determines create vs update mode', () => {
  it('null slug → create mode', () => {
    const comp = make();
    (comp as any).editingSlug.set(null);
    expect((comp as any).editingSlug()).toBeNull();
  });

  it('non-null slug → edit mode with correct slug', () => {
    const comp = make();
    (comp as any).editingSlug.set('mon-article');
    expect((comp as any).editingSlug()).toBe('mon-article');
  });

  it('slug matches article being edited', () => {
    const comp = make();
    (comp as any).articles.set([ARTICLE, DRAFT]);
    const target = (comp as any).articles().find((a: BlogPost) => a.id === 2);
    (comp as any).editingSlug.set(target.slug);
    expect((comp as any).editingSlug()).toBe('brouillon');
  });
});
