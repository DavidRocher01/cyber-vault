import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import { CyberscanService, Scan } from '../services/cyberscan.service';
import { ScoreGaugeComponent } from '../../../shared/score-gauge/score-gauge.component';
import { RadarChartComponent } from '../../../shared/radar-chart/radar-chart.component';
import { computeScore, getGrade, getScoreColor, getCategoryScores, RADAR_CATEGORIES } from '../../../shared/score-utils';

export interface Finding {
  key: string;
  label: string;
  icon: string;
  minTier: number;
  skipped: boolean;
  status: 'OK' | 'WARNING' | 'CRITICAL' | null;
  summary: { label: string; value: string }[];
}

const MODULE_META: { key: string; label: string; icon: string; minTier: number }[] = [
  { key: 'ssl',              label: 'Certificat SSL/TLS',      icon: 'https',         minTier: 1 },
  { key: 'headers',          label: 'Headers HTTP',             icon: 'security',      minTier: 1 },
  { key: 'email',            label: 'Sécurité Email',           icon: 'email',         minTier: 1 },
  { key: 'cookies',          label: 'Cookies',                  icon: 'cookie',        minTier: 1 },
  { key: 'cors',             label: 'CORS',                     icon: 'share',         minTier: 1 },
  { key: 'ip',               label: 'Réputation IP',            icon: 'gps_fixed',     minTier: 1 },
  { key: 'dns',              label: 'DNS / Sous-domaines',      icon: 'dns',           minTier: 1 },
  { key: 'cms',              label: 'Détection CMS',            icon: 'web',           minTier: 1 },
  { key: 'waf',              label: 'Pare-feu (WAF)',           icon: 'shield',        minTier: 1 },
  { key: 'tech',             label: 'Empreinte Tech.',          icon: 'code',          minTier: 3 },
  { key: 'tls',              label: 'Audit TLS',                icon: 'lock',          minTier: 3 },
  { key: 'takeover',         label: 'Subdomain Takeover',       icon: 'warning',       minTier: 3 },
  { key: 'threat_intel',     label: 'Threat Intelligence',      icon: 'bug_report',    minTier: 3 },
  { key: 'http_methods',     label: 'Méthodes HTTP',            icon: 'http',          minTier: 3 },
  { key: 'open_redirect',    label: 'Redirections ouvertes',    icon: 'open_in_new',   minTier: 4 },
  { key: 'clickjacking',     label: 'Clickjacking',             icon: 'layers',        minTier: 4 },
  { key: 'directory_listing',label: 'Listing répertoire',       icon: 'folder_open',   minTier: 4 },
  { key: 'robots',           label: 'Robots / Sitemap',         icon: 'smart_toy',     minTier: 4 },
  { key: 'jwt',              label: 'Tokens JWT',               icon: 'vpn_key',       minTier: 4 },
];

function extractSummary(key: string, d: Record<string, unknown>): { label: string; value: string }[] {
  if (!d || Object.keys(d).length === 0) return [];

  switch (key) {
    case 'ssl':
      return [
        d['issuer']    ? { label: 'Émetteur',     value: String(d['issuer']) }                          : null,
        d['days_left'] != null ? { label: 'Expire dans', value: `${d['days_left']} jours` }             : null,
        d['protocols'] ? { label: 'Protocoles',   value: (d['protocols'] as string[]).join(', ') }      : null,
      ].filter(Boolean) as { label: string; value: string }[];

    case 'headers': {
      const missing = d['missing_headers'] as string[] | undefined;
      return missing?.length
        ? [{ label: 'Headers manquants', value: missing.slice(0, 4).join(', ') }]
        : [{ label: 'Headers manquants', value: 'Aucun' }];
    }

    case 'email': {
      const items = [];
      if (d['spf']  != null) items.push({ label: 'SPF',   value: d['spf']  ? 'Présent' : 'Absent' });
      if (d['dkim'] != null) items.push({ label: 'DKIM',  value: d['dkim'] ? 'Présent' : 'Absent' });
      if (d['dmarc']!= null) items.push({ label: 'DMARC', value: d['dmarc']? 'Présent' : 'Absent' });
      return items;
    }

    case 'cookies': {
      const issues = d['issues'] as string[] | undefined;
      return issues?.length
        ? [{ label: 'Problèmes', value: issues.slice(0, 3).join(', ') }]
        : [{ label: 'Cookies', value: 'Configuration correcte' }];
    }

    case 'cors':
      return d['allow_origin']
        ? [{ label: 'Access-Control-Allow-Origin', value: String(d['allow_origin']).slice(0, 40) }]
        : [{ label: 'CORS', value: 'En-tête absent' }];

    case 'ip':
      return [
        d['ip']        ? { label: 'IP',       value: String(d['ip']) }       : null,
        d['country']   ? { label: 'Pays',     value: String(d['country']) }  : null,
        d['blacklisted'] != null ? { label: 'Blacklist', value: d['blacklisted'] ? 'Oui' : 'Non' } : null,
      ].filter(Boolean) as { label: string; value: string }[];

    case 'dns': {
      const found = d['found'] as { subdomain: string }[] | undefined;
      return found?.length
        ? [{ label: 'Sous-domaines trouvés', value: `${found.length}` }]
        : [{ label: 'Sous-domaines', value: 'Aucun trouvé' }];
    }

    case 'cms':
      return d['cms']
        ? [{ label: 'CMS détecté', value: String(d['cms']) }]
        : [{ label: 'CMS', value: 'Non détecté' }];

    case 'waf':
      return d['waf']
        ? [{ label: 'WAF détecté', value: String(d['waf']) }]
        : [{ label: 'WAF', value: 'Non détecté' }];

    case 'tech': {
      const techs = d['technologies'] as string[] | undefined;
      return techs?.length
        ? [{ label: 'Technologies', value: techs.slice(0, 5).join(', ') }]
        : [];
    }

    case 'tls':
      return [
        d['grade']    ? { label: 'Grade SSL Labs', value: String(d['grade']) } : null,
        d['protocol'] ? { label: 'Protocole min', value: String(d['protocol']) } : null,
      ].filter(Boolean) as { label: string; value: string }[];

    case 'threat_intel': {
      const vulns = d['vulns'] as string[] | undefined;
      const ports  = d['open_ports'] as number[] | undefined;
      return [
        ports?.length  ? { label: 'Ports ouverts',    value: ports.slice(0, 6).join(', ') } : null,
        vulns?.length  ? { label: 'CVE détectées',    value: `${vulns.length}` }             : null,
      ].filter(Boolean) as { label: string; value: string }[];
    }

    case 'http_methods': {
      const dangerous = d['dangerous_methods'] as string[] | undefined;
      return dangerous?.length
        ? [{ label: 'Méthodes dangereuses', value: dangerous.join(', ') }]
        : [{ label: 'Méthodes', value: 'Aucune dangereuse' }];
    }

    case 'jwt': {
      const issues = d['issues'] as string[] | undefined;
      return issues?.length
        ? [{ label: 'Problèmes JWT', value: issues.slice(0, 3).join(', ') }]
        : [{ label: 'JWT', value: 'Aucun token détecté' }];
    }

    default:
      return Object.entries(d)
        .filter(([k, v]) => k !== 'status' && (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean'))
        .slice(0, 3)
        .map(([k, v]) => ({ label: k.replace(/_/g, ' '), value: String(v) }));
  }
}

@Component({
  selector: 'app-scan-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule, MatProgressSpinnerModule, ScoreGaugeComponent, RadarChartComponent],
  templateUrl: './scan-detail.component.html',
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
    interval(4000).pipe(
      switchMap(() => this.cyberscan.getScan(id)),
      takeWhile(s => s.status === 'pending' || s.status === 'running', true),
    ).subscribe(scan => this.scan.set(scan));
  }

  downloadPdf() {
    const s = this.scan();
    if (s) window.open(this.cyberscan.downloadPdf(s.id), '_blank');
  }

  get findings(): Finding[] {
    const scan = this.scan();
    if (!scan?.results_json) return [];
    let r: Record<string, Record<string, unknown>>;
    try { r = JSON.parse(scan.results_json); } catch { return []; }

    const tier = (r['_meta']?.['tier'] as number) ?? 2;

    return MODULE_META.map(m => {
      const data = r[m.key] ?? {};
      const skipped = tier < m.minTier || Object.keys(data).length === 0;
      return {
        ...m,
        skipped,
        status: skipped ? null : (data['status'] as 'OK' | 'WARNING' | 'CRITICAL' | null ?? null),
        summary: skipped ? [] : extractSummary(m.key, data),
      };
    });
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
