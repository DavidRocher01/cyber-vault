import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { pollWithBackoff } from '../../../shared/poll-with-backoff';

import { CyberscanService, Scan } from '../services/cyberscan.service';
import { ScoreGaugeComponent } from '../../../shared/score-gauge/score-gauge.component';
import { RadarChartComponent } from '../../../shared/radar-chart/radar-chart.component';
import { computeScore, getGrade, getScoreColor, getCategoryScores, RADAR_CATEGORIES } from '../../../shared/score-utils';
import { Finding, getFindings } from '../../../shared/scan-findings';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    selector: 'app-scan-detail',
    imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule, MatProgressSpinnerModule, ScoreGaugeComponent, RadarChartComponent, NavButtonsComponent],
    templateUrl: './scan-detail.component.html'
})
export class ScanDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private cyberscan = inject(CyberscanService);

  scan = signal<Scan | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.loadScan(id);
  }

  loadScan(id: number) {
    this.cyberscan.getScan(id).subscribe({
      next: scan => {
        this.scan.set(scan);
        this.loading.set(false);
        if (scan.status === 'pending' || scan.status === 'running') {
          this.startPolling(id);
        }
      },
      error: () => {
        this.error.set('Scan introuvable');
        this.loading.set(false);
      },
    });
  }

  startPolling(id: number) {
    pollWithBackoff(
      () => this.cyberscan.getScan(id),
      s => s.status !== 'pending' && s.status !== 'running',
    ).subscribe(scan => this.scan.set(scan));
  }

  downloadPdf() {
    const s = this.scan();
    if (!s) return;
    this.cyberscan.downloadPdfBlob(s.id).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cyberscan_rapport_${s.id}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: () => console.error('Erreur téléchargement PDF'),
    });
  }

  downloadRemediation(scriptKey: string) {
    const s = this.scan();
    if (!s) return;
    const ext = scriptKey === 'fastapi' ? '.py' : '.sh';
    const filename = `cyberscan_${scriptKey}_${s.id}${ext}`;
    this.cyberscan.downloadRemediationBlob(s.id, scriptKey).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: () => console.error('Erreur téléchargement script'),
    });
  }

  get remediationScripts(): { key: string; label: string; icon: string }[] {
    const results = this.scan()?.results_json;
    if (!results) return [];
    try {
      const parsed = JSON.parse(results);
      const scripts = parsed?._meta?.remediation_scripts ?? {};
      const meta: Record<string, { label: string; icon: string }> = {
        ufw:                   { label: 'Pare-feu UFW',              icon: 'security' },
        ssh:                   { label: 'Durcissement SSH',           icon: 'terminal' },
        robots:                { label: 'robots.txt',                 icon: 'smart_toy' },
        nginx_waf:             { label: 'WAF / Rate-limiting Nginx',  icon: 'shield' },
        fastapi:               { label: 'Middleware FastAPI',         icon: 'code' },
        upgrade:               { label: 'Mises à jour dépendances',   icon: 'system_update' },
        nginx_ssl:             { label: 'SSL/TLS Nginx',              icon: 'lock' },
        fastapi_cors:          { label: 'CORS FastAPI',               icon: 'swap_horiz' },
        nginx_cors:            { label: 'CORS Nginx',                 icon: 'swap_horiz' },
        fastapi_cookie:        { label: 'Cookies sécurisés FastAPI',  icon: 'cookie' },
        nginx_methods:         { label: 'Méthodes HTTP Nginx',        icon: 'http' },
        nginx_clickjacking:    { label: 'Anti-clickjacking Nginx',    icon: 'web_asset_off' },
        fastapi_clickjacking:  { label: 'Anti-clickjacking FastAPI',  icon: 'web_asset_off' },
        nginx_dirlist:         { label: 'Directory listing Nginx',    icon: 'folder_off' },
        fastapi_open_redirect: { label: 'Open redirect FastAPI',      icon: 'link_off' },
        dns_email:             { label: 'SPF / DKIM / DMARC',         icon: 'email' },
      };
      return Object.keys(scripts).filter(k => meta[k]).map(k => ({ key: k, ...meta[k] }));
    } catch { return []; }
  }

  get findings(): Finding[] {
    return getFindings(this.scan()?.results_json ?? null);
  }

  get score(): number | null { return computeScore(this.scan()?.results_json ?? null); }
  get grade(): string { return this.score !== null ? getGrade(this.score) : '—'; }
  get scoreColor(): string { return this.score !== null ? getScoreColor(this.score) : '#6b7280'; }
  get radarScores(): number[] { return getCategoryScores(this.scan()?.results_json ?? null); }
  get radarLabels(): string[] { return RADAR_CATEGORIES.map(c => c.label); }

  get criticalCount(): number {
    return this.findings.filter(f => f.status === 'CRITICAL').length;
  }

  get warningCount(): number {
    return this.findings.filter(f => f.status === 'WARNING').length;
  }

  get duration(): string {
    const s = this.scan();
    if (!s?.started_at || !s?.finished_at) return '—';
    const ms = new Date(s.finished_at).getTime() - new Date(s.started_at).getTime();
    const secs = Math.round(ms / 1000);
    return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m ${secs % 60}s`;
  }

  statusColor(status: string | null): string {
    switch (status) {
      case 'OK':       return 'text-green-400 bg-green-400/10 border-green-600';
      case 'WARNING':  return 'text-yellow-400 bg-yellow-400/10 border-yellow-600';
      case 'CRITICAL': return 'text-red-400 bg-red-400/10 border-red-600';
      default:         return 'text-gray-400 bg-gray-400/10 border-gray-600';
    }
  }

  statusIcon(status: string | null): string {
    switch (status) {
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
}
