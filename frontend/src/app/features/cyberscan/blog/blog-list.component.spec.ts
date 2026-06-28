/**
 * BlogListComponent — tests via injection de dépendances (BlogService mocké).
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { of, throwError } from 'rxjs';
import { Title, Meta } from '@angular/platform-browser';
import { BlogService } from './blog.service';

async function makeComponent(articles = [] as any[], throwErr = false) {
  const { BlogListComponent } = await import('./blog-list.component');

  const titleMock = { setTitle: vi.fn() };
  const metaMock = { updateTag: vi.fn() };
  const blogMock = {
    getAll: vi.fn().mockReturnValue(throwErr ? throwError(() => new Error('err')) : of(articles)),
    formatDate: vi.fn((iso: string) => iso),
  };

  const injector = Injector.create({
    providers: [
      { provide: Title, useValue: titleMock },
      { provide: Meta, useValue: metaMock },
      { provide: BlogService, useValue: blogMock },
    ],
  });

  const comp = runInInjectionContext(injector, () => new BlogListComponent());
  return { comp, titleMock, metaMock, blogMock };
}

describe('BlogListComponent — état initial', () => {
  it('loading est true avant ngOnInit', async () => {
    const { comp } = await makeComponent();
    expect(comp.loading()).toBe(true);
  });

  it('articles est un tableau vide avant ngOnInit', async () => {
    const { comp } = await makeComponent();
    expect(comp.articles()).toEqual([]);
  });

  it('error est false avant ngOnInit', async () => {
    const { comp } = await makeComponent();
    expect(comp.error()).toBe(false);
  });
});

describe('BlogListComponent — ngOnInit() succès', () => {
  const ARTICLES = [
    {
      slug: 'test-slug',
      title: 'Test Article',
      description: 'desc',
      date: '2024-06-01',
      readTime: 5,
      category: 'Test',
      tags: [],
      htmlContent: '<p>html</p>',
    },
  ];

  it('loading passe à false après chargement', async () => {
    const { comp } = await makeComponent(ARTICLES);
    comp.ngOnInit();
    expect(comp.loading()).toBe(false);
  });

  it('articles est rempli après chargement', async () => {
    const { comp } = await makeComponent(ARTICLES);
    comp.ngOnInit();
    expect(comp.articles()).toHaveLength(1);
    expect(comp.articles()[0].slug).toBe('test-slug');
  });

  it('error reste false après un chargement réussi', async () => {
    const { comp } = await makeComponent(ARTICLES);
    comp.ngOnInit();
    expect(comp.error()).toBe(false);
  });

  it('le titre de la page est défini', async () => {
    const { comp, titleMock } = await makeComponent(ARTICLES);
    comp.ngOnInit();
    expect(titleMock.setTitle).toHaveBeenCalledOnce();
    expect(titleMock.setTitle.mock.calls[0][0]).toContain('Blog');
  });

  it('les balises meta sont mises à jour', async () => {
    const { comp, metaMock } = await makeComponent(ARTICLES);
    comp.ngOnInit();
    expect(metaMock.updateTag).toHaveBeenCalled();
  });
});

describe('BlogListComponent — ngOnInit() erreur', () => {
  it('error passe à true si le service échoue', async () => {
    const { comp } = await makeComponent([], true);
    comp.ngOnInit();
    expect(comp.error()).toBe(true);
  });

  it("loading passe à false même en cas d'erreur", async () => {
    const { comp } = await makeComponent([], true);
    comp.ngOnInit();
    expect(comp.loading()).toBe(false);
  });

  it("articles reste vide en cas d'erreur", async () => {
    const { comp } = await makeComponent([], true);
    comp.ngOnInit();
    expect(comp.articles()).toEqual([]);
  });
});

describe('BlogListComponent — formatDate()', () => {
  it('délègue au service BlogService.formatDate()', async () => {
    const { comp, blogMock } = await makeComponent();
    comp.formatDate('2024-06-01');
    expect(blogMock.formatDate).toHaveBeenCalledWith('2024-06-01');
  });
});
