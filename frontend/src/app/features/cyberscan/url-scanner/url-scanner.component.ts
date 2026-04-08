import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { interval, Subscription as RxSubscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import { CyberscanService, UrlScan, PaginatedUrlScans } from '../services/cyberscan.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

interface Finding {
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  time_ms: number | null;
  detail: string;
}

interface UrlScanResults {
  verdict: string;
  threat_type: string | null;
  threat_score: number;
  ssl_valid: boolean;
  original_url: string;
  final_url: string;
  original_domain: string;
  final_domain: string;
  redirect_count: number;
  redirect_chain: string[];
  findings: Finding[];
  screenshot_url: string | null;
}

@Component({
  selector: 'app-url-scanner',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule, NavButtonsComponent,
    MatSnackBarModule, MatPaginatorModule,
  ],
  templateUrl: './url-scanner.component.html',
})
export class UrlScannerComponent implements OnInit, OnDestroy {
  private cyberscan = inject(CyberscanService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private pollSubs: RxSubscription[] = [];

  form = this.fb.nonNullable.group({
    url: ['', [Validators.required, Validators.pattern(/^https?:\/\/.+/)]],
  });

  submitting = signal(false);
  history = signal<PaginatedUrlScans | null>(null);
  loadingHistory = signal(true);
  currentPage = signal(1);
  activeScan = signal<UrlScan | null>(null);

  ngOnInit() {
    this.loadHistory(1);
  }

  ngOnDestroy() {
    this.pollSubs.forEach(s => s.unsubscribe());
  }

  loadHistory(page: number) {
    this.loadingHistory.set(true);
    this.currentPage.set(page);
    this.cyberscan.getUrlScans(page, 20).subscribe({
      next: data => {
        this.history.set(data);
        this.loadingHistory.set(false);
        // Resume polling for any pending/running scans
        data.items
          .filter(s => s.status === 'pending' || s.status === 'running')
          .forEach(s => this.startPolling(s.id));
      },
      error: () => this.loadingHistory.set(false),
    });
  }

  onPageChange(event: PageEvent) {
    this.loadHistory(event.pageIndex + 1);
  }

  submit() {
    if (this.form.invalid) return;
    this.submitting.set(true);

    this.cyberscan.triggerUrlScan(this.form.getRawValue().url).subscribe({
      next: scan => {
        this.submitting.set(false);
        this.form.reset();
        this.activeScan.set(scan);
        this.snack.open('Analyse lancée — résultat dans quelques secondes', 'OK', { duration: 5000 });
        this.startPolling(scan.id);
        this.loadHistory(1);
      },
      error: err => {
        this.submitting.set(false);
        this.snack.open(err.error?.detail || "Erreur lors du lancement", 'Fermer', { duration: 6000 });
      },
    });
  }

  startPolling(scanId: number) {
    const sub = interval(3000).pipe(
      switchMap(() => this.cyberscan.getUrlScan(scanId)),
      takeWhile(s => s.status === 'pending' || s.status === 'running', true),
    ).subscribe(scan => {
      // Update history
      this.history.update(h => {
        if (!h) return h;
        return {
          ...h,
          items: h.items.map(s => s.id === scan.id ? scan : s),
        };
      });
      // Update active scan if it's the one being displayed
      if (this.activeScan()?.id === scan.id) {
        this.activeScan.set(scan);
      }
    });
    this.pollSubs.push(sub);
  }

  deleteScan(scan: UrlScan) {
    this.cyberscan.deleteUrlScan(scan.id).subscribe({
      next: () => {
        this.history.update(h => h ? { ...h, items: h.items.filter(s => s.id !== scan.id), total: h.total - 1 } : h);
        if (this.activeScan()?.id === scan.id) this.activeScan.set(null);
      },
    });
  }

  viewScan(scan: UrlScan) {
    this.activeScan.set(scan);
  }

  getResults(scan: UrlScan): UrlScanResults | null {
    if (!scan.results_json) return null;
    try { return JSON.parse(scan.results_json); } catch { return null; }
  }

  verdictColor(verdict: string | null): string {
    switch (verdict) {
      case 'safe':       return 'text-green-400';
      case 'suspicious': return 'text-yellow-400';
      case 'malicious':  return 'text-red-400';
      default:           return 'text-gray-400';
    }
  }

  verdictBg(verdict: string | null): string {
    switch (verdict) {
      case 'safe':       return 'bg-green-400/10 border-green-700 text-green-400';
      case 'suspicious': return 'bg-yellow-400/10 border-yellow-700 text-yellow-400';
      case 'malicious':  return 'bg-red-400/10 border-red-700 text-red-400';
      default:           return 'bg-gray-700/30 border-gray-600 text-gray-400';
    }
  }

  verdictLabel(verdict: string | null): string {
    switch (verdict) {
      case 'safe':       return 'Sûr';
      case 'suspicious': return 'Suspect';
      case 'malicious':  return 'Malveillant';
      default:           return '—';
    }
  }

  verdictIcon(verdict: string | null): string {
    switch (verdict) {
      case 'safe':       return 'verified_user';
      case 'suspicious': return 'warning';
      case 'malicious':  return 'gpp_bad';
      default:           return 'help_outline';
    }
  }

  threatTypeLabel(type: string | null): string {
    const map: Record<string, string> = {
      phishing: 'Phishing',
      malware: 'Malware',
      redirect: 'Redirection suspecte',
      tracker: 'Tracker',
      malicious_domain: 'Domaine malveillant',
    };
    return type ? (map[type] ?? type) : '—';
  }

  severityColor(sev: string): string {
    switch (sev) {
      case 'critical': return 'text-red-400 bg-red-400/10 border-red-700';
      case 'high':     return 'text-orange-400 bg-orange-400/10 border-orange-700';
      case 'medium':   return 'text-yellow-400 bg-yellow-400/10 border-yellow-700';
      default:         return 'text-gray-400 bg-gray-700/30 border-gray-600';
    }
  }

  severityLabel(sev: string): string {
    const map: Record<string, string> = { critical: 'Critique', high: 'Élevé', medium: 'Moyen', low: 'Faible' };
    return map[sev] ?? sev;
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  scoreGradient(score: number): string {
    if (score >= 66) return '#f87171'; // red
    if (score >= 31) return '#facc15'; // yellow
    return '#4ade80'; // green
  }

  get isRunning(): boolean {
    const s = this.activeScan();
    return !!s && (s.status === 'pending' || s.status === 'running');
  }
}
