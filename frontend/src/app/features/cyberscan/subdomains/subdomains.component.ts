import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';

import { CyberscanService, SubdomainResult, SubdomainEntry } from '../services/cyberscan.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-subdomains',
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatTooltipModule, NavButtonsComponent],
  templateUrl: './subdomains.component.html',
})
export class SubdomainsComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private cyberscan = inject(CyberscanService);

  siteId = signal<number>(0);
  result = signal<SubdomainResult | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  search = signal('');

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.siteId.set(id);
    this.cyberscan.getSiteSubdomains(id).subscribe({
      next: r => { this.result.set(r); this.loading.set(false); },
      error: () => { this.error.set('Impossible de charger les sous-domaines.'); this.loading.set(false); },
    });
  }

  get filtered(): SubdomainEntry[] {
    const q = this.search().toLowerCase();
    return (this.result()?.subdomains ?? []).filter(s =>
      !q || s.subdomain.toLowerCase().includes(q) || s.ip.includes(q)
    );
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
}
