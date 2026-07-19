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
import { PhishingStatusBadgeComponent } from '../phishing-status-badge/phishing-status-badge.component';
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
    PhishingStatusBadgeComponent,
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
  cancelling = signal(false);

  private readonly CANCELLABLE = ['draft', 'pending_verification', 'ready', 'scheduled', 'sending'];
  canCancel(): boolean {
    const s = this.campaign()?.status;
    return !!s && this.CANCELLABLE.includes(s);
  }

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
        this.title.setTitle(`${c.name} — Résultats | Rocher Cybersécurité`);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snack.open('Campagne introuvable', 'Fermer', { duration: 3000 });
        this.router.navigate(['/phishing/campaigns']);
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

  targetStatusLabel(status: string): string {
    const m: Record<string, string> = {
      pending: 'En attente',
      email_sent: 'Envoyé',
      opened: 'Ouvert',
      clicked: 'Cliqué',
      submitted: 'Identifiants saisis',
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
    this.phishingService.downloadPdfBlob(this.campaignId).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `phishing_rapport_${this.campaignId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        this.downloadingPdf.set(false);
      },
      error: () => {
        console.error('Erreur téléchargement PDF');
        this.downloadingPdf.set(false);
      },
    });
  }

  cancel() {
    if (this.cancelling() || !this.canCancel()) return;
    if (!confirm('Annuler cette campagne ? Plus aucun email ne sera envoyé.')) return;
    this.cancelling.set(true);
    this.phishingService.cancelCampaign(this.campaignId).subscribe({
      next: c => {
        this.campaign.set(c);
        this.cancelling.set(false);
        this.snack.open('Campagne annulée', 'OK', { duration: 3000 });
      },
      error: err => {
        this.cancelling.set(false);
        this.snack.open(err.error?.detail || "Erreur lors de l'annulation", 'Fermer', {
          duration: 4000,
        });
      },
    });
  }
}
