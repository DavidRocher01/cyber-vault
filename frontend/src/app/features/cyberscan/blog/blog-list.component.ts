import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { BlogService, BlogArticle } from './blog.service';

@Component({
  standalone: true,
  selector: 'app-blog-list',
  imports: [RouterLink, MatIconModule, MatProgressSpinnerModule, NavButtonsComponent],
  templateUrl: './blog-list.component.html',
})
export class BlogListComponent implements OnInit {
  private titleService = inject(Title);
  private meta = inject(Meta);
  private blog = inject(BlogService);

  articles = signal<BlogArticle[]>([]);
  loading = signal(true);
  error = signal(false);

  ngOnInit() {
    this.titleService.setTitle(
      'Blog cybersécurité — Conseils, audits, bonnes pratiques | CyberScan'
    );
    this.meta.updateTag({
      name: 'description',
      content:
        'Articles sur la cybersécurité des PME : audits, vulnérabilités courantes, RGPD, bonnes pratiques. Rédigés par un développeur-auditeur.',
    });
    this.blog.getAll().subscribe({
      next: data => {
        this.articles.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }

  formatDate(iso: string): string {
    return this.blog.formatDate(iso);
  }
}
