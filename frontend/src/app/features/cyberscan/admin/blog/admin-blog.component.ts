import { Component, inject, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { AdminAuthService } from '../admin-auth.service';

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

@Component({
  standalone: true,
  selector: 'app-admin-blog',
  imports: [ReactiveFormsModule, MatIconModule],
  templateUrl: './admin-blog.component.html',
})
export class AdminBlogComponent implements OnInit {
  private http = inject(HttpClient);
  auth = inject(AdminAuthService);
  private fb = inject(FormBuilder);

  articles = signal<BlogPost[]>([]);
  loading = signal(true);
  view = signal<'list' | 'edit'>('list');
  editingSlug = signal<string | null>(null);
  saving = signal(false);
  saveMsg = signal('');
  saveError = signal('');

  form = this.fb.group({
    slug: ['', Validators.required],
    title: ['', Validators.required],
    description: ['', Validators.required],
    date: ['', Validators.required],
    readTime: [5, Validators.required],
    category: ['', Validators.required],
    tags: [''],
    htmlContent: ['', Validators.required],
    isPublished: [true],
  });

  ngOnInit() {
    this.load();
  }

  load() {
    this.http
      .get<BlogPost[]>('/api/v1/blog/admin/articles', { headers: this.auth.headers() })
      .subscribe({
        next: a => {
          this.articles.set(a);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  openNew() {
    this.editingSlug.set(null);
    this.form.reset({ readTime: 5, isPublished: true });
    this.saveMsg.set('');
    this.saveError.set('');
    this.view.set('edit');
  }

  openEdit(article: BlogPost) {
    this.editingSlug.set(article.slug);
    this.saveMsg.set('');
    this.saveError.set('');
    this.http
      .get<BlogPost>(`/api/v1/blog/admin/articles/${article.slug}`, {
        headers: this.auth.headers(),
      })
      .subscribe({
        next: a => {
          this.form.setValue({
            slug: a.slug,
            title: a.title,
            description: a.description,
            date: a.date,
            readTime: a.readTime,
            category: a.category,
            tags: a.tags.join(', '),
            htmlContent: a.htmlContent ?? '',
            isPublished: a.isPublished,
          });
          this.view.set('edit');
        },
      });
  }

  save() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.value;
    const payload = {
      slug: v.slug!,
      title: v.title!,
      description: v.description!,
      date: v.date!,
      readTime: v.readTime!,
      category: v.category!,
      tags: (v.tags ?? '')
        .split(',')
        .map((t: string) => t.trim())
        .filter(Boolean),
      htmlContent: v.htmlContent!,
      isPublished: v.isPublished ?? true,
    };
    this.saving.set(true);
    this.saveMsg.set('');
    this.saveError.set('');
    const currentSlug = this.editingSlug();
    const req = currentSlug
      ? this.http.put(`/api/v1/blog/admin/articles/${currentSlug}`, payload, {
          headers: this.auth.headers(),
        })
      : this.http.post('/api/v1/blog/admin/articles', payload, { headers: this.auth.headers() });
    req.subscribe({
      next: () => {
        this.saveMsg.set('Enregistré ✓');
        this.saving.set(false);
        this.load();
      },
      error: err => {
        this.saveError.set(err?.error?.detail ?? 'Erreur');
        this.saving.set(false);
      },
    });
  }

  delete(slug: string) {
    this.http
      .delete(`/api/v1/blog/admin/articles/${slug}`, { headers: this.auth.headers() })
      .subscribe({
        next: () => this.articles.update(a => a.filter(x => x.slug !== slug)),
      });
  }

  togglePublish(article: BlogPost) {
    const payload = {
      ...article,
      tags: article.tags,
      htmlContent: article.htmlContent ?? '',
      isPublished: !article.isPublished,
    };
    this.http
      .put(`/api/v1/blog/admin/articles/${article.slug}`, payload, { headers: this.auth.headers() })
      .subscribe({
        next: () =>
          this.articles.update(a =>
            a.map(x => (x.slug === article.slug ? { ...x, isPublished: !x.isPublished } : x))
          ),
      });
  }
}
