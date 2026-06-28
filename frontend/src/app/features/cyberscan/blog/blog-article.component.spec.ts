/**
 * BlogArticleComponent — tests via injection de dépendances (BlogService mocké).
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';
import { Title, Meta } from '@angular/platform-browser';
import { BlogService, BlogArticle } from './blog.service';

const ARTICLE: BlogArticle = {
  slug: 'test-slug',
  title: 'Test Article',
  description: 'Description de test',
  date: '2024-06-01',
  readTime: 5,
  category: 'Sécurité Web',
  tags: ['test'],
  htmlContent: '<p>Contenu de test</p>',
};

async function makeComponent(
  options: {
    slug?: string;
    article?: BlogArticle | null;
    throwErr?: boolean;
  } = {}
) {
  const { BlogArticleComponent } = await import('./blog-article.component');
  const { ActivatedRoute, Router } = await import('@angular/router');

  const navigateMock = vi.fn();
  const titleMock = { setTitle: vi.fn() };
  const metaMock = { updateTag: vi.fn() };
  const blogMock = {
    getBySlug: vi
      .fn()
      .mockReturnValue(
        options.throwErr
          ? throwError(() => new Error('err'))
          : of(options.article !== undefined ? options.article : ARTICLE)
      ),
    formatDate: vi.fn((iso: string) => iso),
  };
  const routeMock = {
    snapshot: {
      paramMap: {
        get: vi.fn((k: string) => (k === 'slug' ? (options.slug ?? 'test-slug') : null)),
      },
    },
  };

  const injector = Injector.create({
    providers: [
      { provide: Title, useValue: titleMock },
      { provide: Meta, useValue: metaMock },
      { provide: BlogService, useValue: blogMock },
      { provide: ActivatedRoute, useValue: routeMock },
      { provide: Router, useValue: { navigate: navigateMock } },
    ],
  });

  const comp = runInInjectionContext(injector, () => new BlogArticleComponent());
  return { comp, navigateMock, titleMock, metaMock, blogMock };
}

describe('BlogArticleComponent — état initial', () => {
  it('loading est true avant ngOnInit', async () => {
    const { comp } = await makeComponent();
    expect(comp.loading()).toBe(true);
  });

  it('article est null avant ngOnInit', async () => {
    const { comp } = await makeComponent();
    expect(comp.article()).toBeNull();
  });
});

describe('BlogArticleComponent — ngOnInit() succès avec article', () => {
  it('loading passe à false après chargement', async () => {
    const { comp } = await makeComponent();
    comp.ngOnInit();
    expect(comp.loading()).toBe(false);
  });

  it('article est rempli après chargement', async () => {
    const { comp } = await makeComponent();
    comp.ngOnInit();
    expect(comp.article()).not.toBeNull();
    expect(comp.article()?.slug).toBe('test-slug');
  });

  it('le titre de la page est mis à jour', async () => {
    const { comp, titleMock } = await makeComponent();
    comp.ngOnInit();
    expect(titleMock.setTitle).toHaveBeenCalledOnce();
    expect(titleMock.setTitle.mock.calls[0][0]).toContain('Test Article');
  });

  it('les balises meta sont mises à jour', async () => {
    const { comp, metaMock } = await makeComponent();
    comp.ngOnInit();
    expect(metaMock.updateTag).toHaveBeenCalled();
  });

  it("ne redirige pas quand l'article est trouvé", async () => {
    const { comp, navigateMock } = await makeComponent();
    comp.ngOnInit();
    expect(navigateMock).not.toHaveBeenCalled();
  });
});

describe('BlogArticleComponent — ngOnInit() article non trouvé', () => {
  it('redirige vers /cyberscan/blog si article null', async () => {
    const { comp, navigateMock } = await makeComponent({ article: null });
    comp.ngOnInit();
    expect(navigateMock).toHaveBeenCalledWith(['/cyberscan/blog']);
  });

  it('article reste null après redirection', async () => {
    const { comp } = await makeComponent({ article: null });
    comp.ngOnInit();
    expect(comp.article()).toBeNull();
  });
});

describe('BlogArticleComponent — ngOnInit() erreur', () => {
  it("redirige vers /cyberscan/blog en cas d'erreur", async () => {
    const { comp, navigateMock } = await makeComponent({ throwErr: true });
    comp.ngOnInit();
    expect(navigateMock).toHaveBeenCalledWith(['/cyberscan/blog']);
  });

  it("loading passe à false même en cas d'erreur", async () => {
    const { comp } = await makeComponent({ throwErr: true });
    comp.ngOnInit();
    expect(comp.loading()).toBe(false);
  });
});

describe('BlogArticleComponent — formatDate()', () => {
  it('délègue au service BlogService.formatDate()', async () => {
    const { comp, blogMock } = await makeComponent();
    comp.formatDate('2024-06-01');
    expect(blogMock.formatDate).toHaveBeenCalledWith('2024-06-01');
  });
});
