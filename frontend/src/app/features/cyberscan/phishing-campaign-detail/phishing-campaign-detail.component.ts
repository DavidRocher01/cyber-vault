import { Component, OnInit, inject, signal, DestroyRef } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { interval, EMPTY } from 'rxjs';
import { switchMap } from 'rxjs/operators';

import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { PhishingService, PhishingCampaign } from '../services/phishing.service';
import { PHISHING_SCENARIOS } from '../phishing/phishing.component';

@Component({
  standalone: true,
  selector: 'app-phishing-campaign-detail',
  imports: [
    TitleCasePipe,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    NavButtonsComponent,
  ],
  templateUrl: './phishing-campaign-detail.component.html',
})
export class PhishingCampaignDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private phishingService = inject(PhishingService);
  private snack = inject(MatSnackBar);
  private title = inject(Title);
  private destroyRef = inject(DestroyRef);

  campaignId = 0;
  campaign = signal<PhishingCampaign | null>(null);
  loading = signal(true);
  downloadingPdf = signal(false);

  readonly scenarios = PHISHING_SCENARIOS;

  ngOnInit() {
    this.campaignId = Number(this.route.snapshot.paramMap.get('id'));
    this.load();

    // Live polling: 5s while sending (progress bar), 5s while active (stats)
    // Returns EMPTY when campaign is completed/draft to avoid unnecessary API calls
    interval(5_000)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        switchMap(() => {
          const s = this.campaign()?.status;
          return s === 'sending' || s === 'active'
            ? this.phishingService.getCampaign(this.campaignId)
            : EMPTY;
        })
      )
      .subscribe(c => this.campaign.set(c));
  }

  load() {
    this.loading.set(true);
    this.phishingService.getCampaign(this.campaignId).subscribe({
      next: c => {
        this.campaign.set(c);
        this.title.setTitle(`${c.name} — Résultats | CyberScan`);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snack.open('Campagne introuvable', 'Fermer', { duration: 3000 });
        this.router.navigate(['/cyberscan/phishing/campaigns']);
      },
    });
  }

  openRate(c: PhishingCampaign): number {
    return c.emails_sent ? Math.round((c.opened_count / c.emails_sent) * 100) : 0;
  }

  clickRate(c: PhishingCampaign): number {
    return c.emails_sent ? Math.round((c.clicked_count / c.emails_sent) * 100) : 0;
  }

  submitRate(c: PhishingCampaign): number {
    return c.emails_sent ? Math.round((c.submitted_count / c.emails_sent) * 100) : 0;
  }

  sendProgress(c: PhishingCampaign): number {
    return c.targets_count ? Math.round((c.emails_sent / c.targets_count) * 100) : 0;
  }

  riskLevel(c: PhishingCampaign): { label: string; color: string } {
    const r = this.clickRate(c);
    if (r >= 30) return { label: 'Risque élevé', color: 'text-red-400' };
    if (r >= 15) return { label: 'Risque modéré', color: 'text-yellow-400' };
    if (r > 0) return { label: 'Risque faible', color: 'text-green-400' };
    return { label: '—', color: 'text-gray-500' };
  }

  statusLabel(status: string): string {
    const m: Record<string, string> = {
      draft: 'Brouillon',
      pending_verification: 'Vérification',
      ready: 'Prête',
      scheduled: 'Planifiée',
      sending: 'Envoi en cours',
      active: 'En cours',
      completed: 'Terminée',
      cancelled: 'Annulée',
    };
    return m[status] ?? status;
  }

  statusColor(status: string): string {
    switch (status) {
      case 'active':
      case 'sending':
        return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
      case 'completed':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'draft':
        return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
      case 'ready':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      case 'scheduled':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
      case 'cancelled':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      default:
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    }
  }

  targetStatusLabel(status: string): string {
    const m: Record<string, string> = {
      pending: 'En attente',
      email_sent: 'Envoyé',
      opened: 'Ouvert',
      clicked: 'Cliqué',
      submitted: 'Identifiants saisis',
      reported: 'Signalé',
    };
    return m[status] ?? status;
  }

  targetStatusColor(status: string): string {
    switch (status) {
      case 'submitted':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 'clicked':
        return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
      case 'opened':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      case 'email_sent':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      case 'reported':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      default:
        return 'text-gray-500 bg-gray-500/10 border-gray-500/30';
    }
  }

  lastEventAt(t: import('../services/phishing.service').PhishingTarget): string {
    return this.formatDate(t.submitted_at ?? t.clicked_at ?? t.opened_at ?? t.email_sent_at);
  }

  scenarioName(key: string): string {
    return this.scenarios.find(s => s.id === key)?.name ?? key;
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  downloadPdf() {
    this.downloadingPdf.set(true);
    window.open(this.phishingService.getPdfUrl(this.campaignId), '_blank');
    setTimeout(() => this.downloadingPdf.set(false), 2000);
  }
}
