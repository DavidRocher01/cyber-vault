import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { Subscription as RxSubscription } from 'rxjs';
import { pollWithBackoff } from '../../../shared/poll-with-backoff';

import { CyberscanService, Site, Scan, PaginatedScans } from '../services/cyberscan.service';
import { ScoreGaugeComponent } from '../../../shared/score-gauge/score-gauge.component';
import { computeScore, getGrade, getScoreColor } from '../../../shared/score-utils';
import { Finding, getFindings } from '../../../shared/scan-findings';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { ScoreTrendComponent, ScoreTrendPoint } from '../../../shared/score-trend/score-trend.component';

@Component({
    standalone: true,
    selector: 'app-site-detail',
    imports: [
        CommonModule, RouterLink,
        MatButtonModule, MatIconModule, MatProgressSpinnerModule,
        MatSnackBarModule, MatPaginatorModule, ScoreGaugeComponent, NavButtonsComponent, ScoreTrendComponent,
    ],
    templateUrl: './site-detail.component.html'
})
export class SiteDetailComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private cyberscan = inject(CyberscanService);
  private snack = inject(MatSnackBar);
  private pollingSubscription?: RxSubscription;

  siteId = signal<number>(0);
  site = signal<Site | null>(null);
  scans = signal<PaginatedScans | null>(null);
  loading = signal(true);
  loadingScans = signal(false);
  triggering = signal(false);
  currentPage = signal(1);
  activeTab = signal<'failles' | 'historique' | 'rapports'>('failles');

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.siteId.set(id);
    this.loadSite(id);
  }

  ngOnDestroy() {
    this.pollingSubscription?.unsubscribe();
  }

  loadSite(id: number) {
    this.loading.set(true);
    this.cyberscan.getMySites().subscribe({
      next: sites => {
        const found = sites.find(s => s.id === id) ?? null;
        this.site.set(found);
        this.loading.set(false);
        this.loadScans(1);
      },
      error: () => this.loading.set(false),
    });
  }

  loadScans(page: number) {
    this.loadingScans.set(true);
    this.currentPage.set(page);
    this.cyberscan.getSiteScans(this.siteId(), page, 20).subscribe({
      next: data => {
        this.scans.set(data);
        this.loadingScans.set(false);
        this.maybeStartPolling(data.items);
      },
      error: () => this.loadingScans.set(false),
    });
  }

  onPageChange(event: PageEvent) {
    this.loadScans(event.pageIndex + 1);
  }

  maybeStartPolling(items: Scan[]) {
    const hasActive = items.some(s => s.status === 'pending' || s.status === 'running');
    if (!hasActive || this.pollingSubscription) return;
    this.pollingSubscription = pollWithBackoff(
      () => this.cyberscan.getSiteScans(this.siteId(), this.currentPage(), 20),
      d => !d.items.some(s => s.status === 'pending' || s.status === 'running'),
    ).subscribe(data => {
      this.scans.set(data);
      if (!data.items.some(s => s.status === 'pending' || s.status === 'running')) {
        this.pollingSubscription?.unsubscribe();
        this.pollingSubscription = undefined;
      }
    });
  }

  triggerScan() {
    this.triggering.set(true);
    this.cyberscan.triggerScan(this.siteId()).subscribe({
      next: () => {
        this.triggering.set(false);
        this.snack.open('Scan lancé — mise à jour automatique en cours', 'OK', { duration: 5000 });
        this.loadScans(1);
      },
      error: err => {
        this.triggering.set(false);
        this.snack.open(err.error?.detail || 'Erreur lors du lancement', 'Fermer', { duration: 6000 });
      },
    });
  }

  downloadPdf(scanId: number) {
    this.cyberscan.downloadPdfBlob(scanId).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cyberscan_rapport_${scanId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: () => this.snack.open('Erreur lors du téléchargement du PDF', 'Fermer', { duration: 4000 }),
    });
  }


  // ── Computed helpers ──────────────────────────────────────────

  get latestDoneScan(): Scan | null {
    return this.scans()?.items.find(s => s.status === 'done' && s.results_json) ?? null;
  }

  get latestScore(): number | null {
    return computeScore(this.latestDoneScan?.results_json ?? null);
  }

  get latestGrade(): string {
    return this.latestScore !== null ? getGrade(this.latestScore) : '—';
  }

  get latestScoreColor(): string {
    return this.latestScore !== null ? getScoreColor(this.latestScore) : '#6b7280';
  }

  get findings(): Finding[] {
    return getFindings(this.latestDoneScan?.results_json ?? null);
  }

  get criticalFindings(): Finding[] {
    return this.findings.filter(f => f.status === 'CRITICAL');
  }

  get warningFindings(): Finding[] {
    return this.findings.filter(f => f.status === 'WARNING');
  }

  get alertFindings(): Finding[] {
    return this.findings.filter(f => f.status === 'CRITICAL' || f.status === 'WARNING');
  }

  get pdfScans(): Scan[] {
    return (this.scans()?.items ?? []).filter(s => s.pdf_path);
  }

  get hasActiveScans(): boolean {
    return (this.scans()?.items ?? []).some(s => s.status === 'pending' || s.status === 'running');
  }

  get scoreTrend(): ScoreTrendPoint[] {
    return (this.scans()?.items ?? [])
      .filter(s => s.status === 'done' && s.results_json && s.finished_at)
      .map(s => ({ date: s.finished_at!, score: computeScore(s.results_json) ?? 0 }))
      .filter(p => p.score > 0);
  }

  getScanScore(scan: Scan): number | null {
    return computeScore(scan.results_json ?? null);
  }

  getScanCriticalCount(scan: Scan): number {
    return getFindings(scan.results_json ?? null).filter(f => f.status === 'CRITICAL').length;
  }

  getScanWarningCount(scan: Scan): number {
    return getFindings(scan.results_json ?? null).filter(f => f.status === 'WARNING').length;
  }

  statusColor(s: string | null): string {
    switch (s) {
      case 'OK':       return 'text-green-400 bg-green-400/10 border-green-700';
      case 'WARNING':  return 'text-yellow-400 bg-yellow-400/10 border-yellow-700';
      case 'CRITICAL': return 'text-red-400 bg-red-400/10 border-red-700';
      case 'done':     return 'text-green-400';
      case 'pending': case 'running': return 'text-blue-400';
      case 'error':    return 'text-red-400';
      default:         return 'text-gray-400 bg-gray-700/30 border-gray-600';
    }
  }

  statusIcon(s: string | null): string {
    switch (s) {
      case 'OK':       return 'verified_user';
      case 'WARNING':  return 'warning';
      case 'CRITICAL': return 'gpp_bad';
      case 'done':     return 'check_circle';
      case 'pending':  return 'schedule';
      case 'running':  return 'sync';
      case 'error':    return 'cancel';
      default:         return 'help_outline';
    }
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  formatDateShort(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }
}
