import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { PhishingService, PhishingCampaign } from '../services/phishing.service';

@Component({
  standalone: true,
  selector: 'app-phishing-campaigns',
  imports: [
    CommonModule, RouterLink,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule,
    NavButtonsComponent,
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
    this.title.setTitle('Simulation de phishing — Mes campagnes | CyberScan');
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.phishingService.getCampaigns().subscribe({
      next: c => { this.campaigns.set(c); this.loading.set(false); },
      error: () => { this.loading.set(false); this.snack.open('Erreur lors du chargement', 'Fermer', { duration: 3000 }); },
    });
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: 'Brouillon',
      pending_verification: 'Vérification domaine',
      ready: 'Prête',
      sending: 'Envoi en cours',
      active: 'En cours',
      completed: 'Terminée',
      cancelled: 'Annulée',
    };
    return labels[status] ?? status;
  }

  statusColor(status: string): string {
    switch (status) {
      case 'active':
      case 'sending':    return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
      case 'completed':  return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'draft':      return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
      case 'ready':      return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      case 'cancelled':  return 'text-red-400 bg-red-500/10 border-red-500/30';
      default:           return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    }
  }

  clickRateLabel(campaign: PhishingCampaign): string {
    if (!campaign.targets_count || campaign.status === 'draft') return '—';
    return `${Math.round(campaign.click_rate * 100)} %`;
  }

  clickRateColor(campaign: PhishingCampaign): string {
    if (!campaign.targets_count || campaign.status === 'draft') return 'text-gray-500';
    if (campaign.click_rate >= 0.30) return 'text-red-400 font-semibold';
    if (campaign.click_rate >= 0.15) return 'text-yellow-400 font-semibold';
    return 'text-green-400 font-semibold';
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }
}
