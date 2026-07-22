import { Component, OnInit, inject, signal } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { PhishingStatusBadgeComponent } from '../phishing-status-badge/phishing-status-badge.component';
import { PhishingService, PhishingCampaign } from '../services/phishing.service';
import { extractApiError } from '../../../core/http-error';

interface TrendPoint {
  label: string;
  date: string;
  openRate: number;
  clickRate: number;
  submitRate: number;
}

@Component({
  standalone: true,
  selector: 'app-phishing-campaigns',
  imports: [
    TitleCasePipe,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    NavButtonsComponent,
    PhishingStatusBadgeComponent,
  ],
  templateUrl: './phishing-campaigns.component.html',
})
export class PhishingCampaignsComponent implements OnInit {
  private phishingService = inject(PhishingService);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  campaigns = signal<PhishingCampaign[]>([]);
  loading = signal(true);

  ngOnInit() {
    this.title.setTitle('Simulation de phishing — Mes campagnes | Rocher Cybersécurité');
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.phishingService.getCampaigns().subscribe({
      next: c => {
        this.campaigns.set(c);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snack.open('Erreur lors du chargement', 'Fermer', { duration: 3000 });
      },
    });
  }

  deleteCampaign(id: number, name: string, event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    if (!confirm(`Supprimer définitivement la campagne « ${name} » ?`)) return;
    this.phishingService.deleteCampaign(id).subscribe({
      next: () => {
        this.campaigns.update(list => list.filter(c => c.id !== id));
        this.snack.open('Campagne supprimée', 'OK', { duration: 3000 });
      },
      error: err =>
        this.snack.open(extractApiError(err, 'Suppression impossible'), 'Fermer', {
          duration: 4000,
        }),
    });
  }

  clickRateLabel(campaign: PhishingCampaign): string {
    if (!campaign.targets_count || campaign.status === 'draft') return '—';
    return `${Math.round(campaign.click_rate * 100)} %`;
  }

  clickRateColor(campaign: PhishingCampaign): string {
    if (!campaign.targets_count || campaign.status === 'draft') return 'text-gray-500';
    if (campaign.click_rate >= 0.3) return 'text-red-400 font-semibold';
    if (campaign.click_rate >= 0.15) return 'text-yellow-400 font-semibold';
    return 'text-green-400 font-semibold';
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  get trendData(): TrendPoint[] {
    return this.campaigns()
      .filter(c => c.emails_sent > 0)
      .sort(
        (a, b) =>
          new Date(a.started_at ?? a.created_at).getTime() -
          new Date(b.started_at ?? b.created_at).getTime()
      )
      .map(c => ({
        label: c.name.length > 12 ? c.name.slice(0, 12) + '…' : c.name,
        date: this.formatDate(c.started_at),
        openRate: c.emails_sent ? Math.round((c.opened_count / c.emails_sent) * 100) : 0,
        clickRate: Math.round(c.click_rate * 100),
        submitRate: c.emails_sent ? Math.round((c.submitted_count / c.emails_sent) * 100) : 0,
      }));
  }

  trendPolyline(metric: 'openRate' | 'clickRate' | 'submitRate', pts: TrendPoint[]): string {
    if (!pts.length) return '';
    const n = pts.length;
    return pts
      .map((d, i) => {
        const x = n === 1 ? 200 : (i / (n - 1)) * 400;
        const y = 84 - (d[metric] / 100) * 80;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }

  trendDotX(i: number, n: number): number {
    return n === 1 ? 200 : (i / (n - 1)) * 400;
  }

  trendDotY(rate: number): number {
    return 84 - (rate / 100) * 80;
  }

  trendXPct(i: number, n: number): number {
    return n === 1 ? 50 : (i / (n - 1)) * 100;
  }
}
