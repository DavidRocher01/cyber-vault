import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

export interface BlogArticle {
  slug: string;
  title: string;
  description: string;
  date: string;
  readTime: number;
  category: string;
  tags: string[];
  htmlContent: string;
}

// Fallback articles shown while the API is loading or unreachable
export const FALLBACK_ARTICLES: BlogArticle[] = [
  {
    slug: 'audit-cybersecurite-pme-prix-2026',
    title: 'Audit cybersécurité PME : combien ça coûte vraiment en 2026 ?',
    description: 'Tarifs détaillés, types d\'audits, ce qui est inclus et le ROI pour une TPE/PME. Guide complet par un développeur-auditeur basé en Auvergne-Rhône-Alpes.',
    date: '2026-05-01',
    readTime: 8,
    category: 'Audit & Conseils',
    tags: ['audit cybersécurité', 'PME', 'prix', 'pentest', 'RGPD'],
    htmlContent: '<p>Contenu en cours de chargement...</p>',
  },
  {
    slug: 'vulnerabilites-courantes-sites-ecommerce',
    title: 'Les 10 vulnérabilités les plus courantes sur les sites e-commerce français',
    description: 'XSS, injection SQL, mauvaise config SSL... Les failles que l\'on trouve à 90 % sur les sites e-commerce lors de nos audits. Exemples concrets et solutions.',
    date: '2026-05-12',
    readTime: 10,
    category: 'Sécurité Web',
    tags: ['e-commerce', 'XSS', 'injection SQL', 'OWASP', 'sécurité web'],
    htmlContent: '<p>Contenu en cours de chargement...</p>',
  },
];

@Injectable({ providedIn: 'root' })
export class BlogService {
  http = inject(HttpClient);

  getAll(): Observable<BlogArticle[]> {
    return this.http.get<any[]>('/api/v1/blog/articles').pipe(
      map(posts => posts.sort((a, b) => b.date.localeCompare(a.date))),
      catchError(() => of([...FALLBACK_ARTICLES].sort((a, b) => b.date.localeCompare(a.date)))),
    );
  }

  getBySlug(slug: string): Observable<BlogArticle | null> {
    return this.http.get<BlogArticle>(`/api/v1/blog/articles/${slug}`).pipe(
      catchError(() => {
        const found = FALLBACK_ARTICLES.find(a => a.slug === slug) ?? null;
        return of(found);
      }),
    );
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
  }
}
