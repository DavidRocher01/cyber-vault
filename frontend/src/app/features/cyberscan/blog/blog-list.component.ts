import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AsyncPipe } from '@angular/common';
import { Title, Meta } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { BlogService } from './blog.service';

@Component({
  standalone: true,
  selector: 'app-blog-list',
  imports: [RouterLink, AsyncPipe, MatIconModule, NavButtonsComponent],
  templateUrl: './blog-list.component.html',
})
export class BlogListComponent implements OnInit {
  private titleService = inject(Title);
  private meta = inject(Meta);
  readonly blog = inject(BlogService);

  readonly articles$ = this.blog.getAll();

  ngOnInit() {
    this.titleService.setTitle(
      'Blog cybersécurité — Conseils, audits, bonnes pratiques | CyberScan'
    );
    this.meta.updateTag({
      name: 'description',
      content:
        'Articles sur la cybersécurité des PME : audits, vulnérabilités courantes, RGPD, bonnes pratiques. Rédigés par un développeur-auditeur.',
    });
  }

  formatDate(iso: string): string {
    return this.blog.formatDate(iso);
  }
}
