import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { BlogService, BlogArticle } from './blog.service';

@Component({
  standalone: true,
  selector: 'app-blog-article',
  imports: [RouterLink, MatIconModule, MatProgressSpinnerModule, NavButtonsComponent],
  templateUrl: './blog-article.component.html',
})
export class BlogArticleComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private titleService = inject(Title);
  private meta = inject(Meta);
  private blog = inject(BlogService);

  article = signal<BlogArticle | null>(null);
  loading = signal(true);

  ngOnInit() {
    const slug = this.route.snapshot.paramMap.get('slug') ?? '';
    this.blog.getBySlug(slug).subscribe({
      next: found => {
        this.loading.set(false);
        if (!found) {
          this.router.navigate(['/blog']);
          return;
        }
        this.article.set(found);
        this.titleService.setTitle(`${found.title} | Rocher Cybersécurité Blog`);
        this.meta.updateTag({ name: 'description', content: found.description });
        this.meta.updateTag({ property: 'og:title', content: found.title });
        this.meta.updateTag({ property: 'og:description', content: found.description });
        this.meta.updateTag({ name: 'robots', content: 'index, follow' });
      },
      error: () => {
        this.loading.set(false);
        this.router.navigate(['/blog']);
      },
    });
  }

  formatDate(iso: string): string {
    return this.blog.formatDate(iso);
  }
}
