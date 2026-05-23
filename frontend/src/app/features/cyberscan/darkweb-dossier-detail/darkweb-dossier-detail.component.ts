import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Title } from '@angular/platform-browser';

import {
  DarkwebDossierService,
  DossierDetail,
  DossierTarget,
  BreachSource,
} from '../services/darkweb-dossier.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-darkweb-dossier-detail',
  imports: [
    RouterLink,
    MatButtonModule, MatExpansionModule, MatIconModule,
    MatProgressSpinnerModule, MatSnackBarModule, MatTooltipModule,
    NavButtonsComponent,
  ],
  templateUrl: './darkweb-dossier-detail.component.html',
})
export class DarkwebDossierDetailComponent implements OnInit, OnDestroy {
  private service = inject(DarkwebDossierService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  dossier = signal<DossierDetail | null>(null);
  loading = signal(true);
  downloadingPdf = signal(false);
  downloadingCsv = signal(false);
  rescanning = signal(false);
  togglingMonitor = signal(false);
  private pollInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit() {
    this.title.setTitle('Dossier Dark Web — CyberScan');
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) { this.router.navigate(['/cyberscan/darkweb-dossier']); return; }
    this.loadDossier(id);
  }

  ngOnDestroy() {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  private loadDossier(id: number) {
    this.service.get(id).subscribe({
      next: d => {
        this.dossier.set(d);
        this.loading.set(false);
        if (d.status === 'pending' || d.status === 'processing') {
          this.startPolling(id);
        }
      },
      error: () => {
        this.loading.set(false);
        this.router.navigate(['/cyberscan/darkweb-dossier']);
      },
    });
  }

  private startPolling(id: number) {
    if (this.pollInterval) return;
    this.pollInterval = setInterval(() => {
      this.service.get(id).subscribe({
        next: d => {
          this.dossier.set(d);
          if (d.status === 'completed' || d.status === 'failed') {
            clearInterval(this.pollInterval!);
            this.pollInterval = null;
            this.rescanning.set(false);
          }
        },
      });
    }, 5000);
  }

  rescan() {
    const d = this.dossier();
    if (!d || this.rescanning()) return;
    this.rescanning.set(true);
    this.service.rescan(d.id).subscribe({
      next: updated => {
        this.dossier.set(updated);
        this.snack.open('Rescan lancé — analyse en cours…', 'OK', { duration: 4000 });
        this.startPolling(d.id);
      },
      error: (err) => {
        this.rescanning.set(false);
        this.snack.open(err?.error?.detail || 'Erreur lors du rescan', 'Fermer', { duration: 4000 });
      },
    });
  }

  toggleMonitor() {
    const d = this.dossier();
    if (!d || this.togglingMonitor()) return;
    this.togglingMonitor.set(true);
    this.service.toggleMonitor(d.id).subscribe({
      next: res => {
        this.dossier.set({ ...d, monitor_active: res.monitor_active, next_monitor_at: res.next_monitor_at });
        this.togglingMonitor.set(false);
        const msg = res.monitor_active
          ? 'Monitoring mensuel activé — vous serez alerté en cas de nouvelle fuite'
          : 'Monitoring désactivé';
        this.snack.open(msg, 'OK', { duration: 4000 });
      },
      error: () => {
        this.togglingMonitor.set(false);
        this.snack.open('Erreur lors du changement de monitoring', 'Fermer', { duration: 3000 });
      },
    });
  }

  downloadPdf() {
    const d = this.dossier();
    if (!d) return;
    this.downloadingPdf.set(true);
    this._downloadFile(this.service.getPdfUrl(d.id), `dossier-darkweb-${d.domain}.pdf`)
      .finally(() => this.downloadingPdf.set(false));
  }

  downloadCsv() {
    const d = this.dossier();
    if (!d) return;
    this.downloadingCsv.set(true);
    this._downloadFile(this.service.getCsvUrl(d.id), `dossier-darkweb-${d.domain}.csv`)
      .finally(() => this.downloadingCsv.set(false));
  }

  private _downloadFile(url: string, filename: string): Promise<void> {
    return fetch(url, { credentials: 'include' })
      .then(r => r.blob())
      .then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch(() => {
        this.snack.open('Erreur lors du téléchargement', 'Fermer', { duration: 3000 });
      });
  }

  getBreaches(target: DossierTarget): BreachSource[] {
    return this.service.parseBreachSources(target.breach_sources_json);
  }

  getTopSources(): { name: string; count: number }[] {
    return this.service.parseTopSources(this.dossier()?.top_sources_json ?? null);
  }

  getBreachTimeline(): { year: number; count: number }[] {
    return this.service.buildBreachTimeline(this.dossier()?.targets ?? []);
  }

  getBreachTimelineMax(timeline: { year: number; count: number }[]): number {
    return timeline.reduce((m, t) => Math.max(m, t.count), 1);
  }

  exposedTargets(): DossierTarget[] {
    return (this.dossier()?.targets ?? []).filter(t => t.status === 'exposed');
  }

  cleanTargets(): DossierTarget[] {
    return (this.dossier()?.targets ?? []).filter(t => t.status === 'clean');
  }

  riskColor(score: number | null): string {
    if (score === null) return 'text-gray-400';
    if (score >= 50) return 'text-red-400';
    if (score >= 20) return 'text-yellow-400';
    return 'text-green-400';
  }

  riskBorderColor(score: number | null): string {
    if (score === null) return 'border-gray-700/40';
    if (score >= 50) return 'border-red-700/40';
    if (score >= 20) return 'border-yellow-700/40';
    return 'border-green-700/40';
  }

  riskLabel(score: number | null): string {
    if (score === null) return 'Non calculé';
    if (score >= 50) return 'Risque élevé';
    if (score >= 20) return 'Risque modéré';
    return 'Risque faible';
  }

  severityColor(score: number | null): string {
    if (score === null) return 'text-gray-400';
    if (score >= 60) return 'text-red-400';
    if (score >= 30) return 'text-orange-400';
    return 'text-yellow-400';
  }

  severityLabel(score: number | null): string {
    if (score === null) return 'Non calculé';
    if (score >= 60) return 'Données critiques exposées';
    if (score >= 30) return 'Données sensibles exposées';
    return 'Données peu sensibles';
  }

  breachCountColor(count: number): string {
    if (count >= 3) return 'text-red-400';
    if (count >= 1) return 'text-yellow-400';
    return 'text-green-400';
  }

  statusLabel(status: string): string {
    switch (status) {
      case 'pending': return 'En attente';
      case 'processing': return 'Analyse en cours';
      case 'completed': return 'Terminé';
      case 'failed': return 'Erreur';
      default: return status;
    }
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  formatPwnCount(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
    return n > 0 ? n.toString() : '—';
  }
}
