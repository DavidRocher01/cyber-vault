import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Title, Meta } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { BlogService, BlogArticle } from './blog.service';

@Component({
  standalone: true,
  selector: 'app-blog-article',
  imports: [RouterLink, CommonModule, MatIconModule, NavButtonsComponent],
  templateUrl: './blog-article.component.html',
})
export class BlogArticleComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private titleService = inject(Title);
  private meta = inject(Meta);
  private blog = inject(BlogService);

  article: BlogArticle | null = null;

  ngOnInit() {
    const slug = this.route.snapshot.paramMap.get('slug') ?? '';
    this.blog.getBySlug(slug).subscribe(found => {
      if (!found) {
        this.router.navigate(['/cyberscan/blog']);
        return;
      }
      this.article = found;
      this.titleService.setTitle(`${found.title} | CyberScan Blog`);
      this.meta.updateTag({ name: 'description', content: found.description });
      this.meta.updateTag({ property: 'og:title', content: found.title });
      this.meta.updateTag({ property: 'og:description', content: found.description });
      this.meta.updateTag({ name: 'robots', content: 'index, follow' });
    });
  }

  formatDate(iso: string): string {
    return this.blog.formatDate(iso);
  }
}
