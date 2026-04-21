import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Subscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import { CyberscanService, PublicScanResult } from '../services/cyberscan.service';
import { ScoreGaugeComponent } from '../../../shared/score-gauge/score-gauge.component';
import { computeScore, getGrade, getScoreColor } from '../../../shared/score-utils';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

interface ModuleResult {
  key: string;
  label: string;
  icon: string;
  status: string | null;
  detail?: string;
}

@Component({
  standalone: true,
  selector: 'app-demo-result',
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule, MatProgressSpinnerModule, ScoreGaugeComponent, NavButtonsComponent],
  templateUrl: './demo-result.component.html',
})
export class DemoResultComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private cyberscan = inject(CyberscanService);

  scan = signal<PublicScanResult | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);

  private pollSub: Subscription | null = null;

  ngOnInit() {
    const token = this.route.snapshot.paramMap.get('token');
    if (!token) { this.router.navigate(['/cyberscan']); return; }

    this.pollSub = interval(3000).pipe(
      switchMap(() => this.cyberscan.getPublicScan(token)),
      takeWhile(s => s.status === 'pending' || s.status === 'running', true),
    ).subscribe({
      next: s => {
        this.scan.set(s);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Scan introuvable ou expiré.');
        this.loading.set(false);
      },
    });

    // First immediate fetch
    this.cyberscan.getPublicScan(token).subscribe({
      next: s => { this.scan.set(s); this.loading.set(false); },
      error: () => { this.error.set('Scan introuvable.'); this.loading.set(false); },
    });
  }

  ngOnDestroy() { this.pollSub?.unsubscribe(); }

  get score(): number | null { return computeScore(this.scan()?.results_json ?? null); }
  getGrade(s: number) { return getGrade(s); }
  getScoreColor(s: number) { return getScoreColor(s); }

  get isRunning(): boolean {
    const s = this.scan()?.status;
    return s === 'pending' || s === 'running';
  }

  get modules(): ModuleResult[] {
    const json = this.scan()?.results_json;
    if (!json) return [];
    try {
      const r = JSON.parse(json);
      return [
        { key: 'ssl',     label: 'Certificat SSL',    icon: 'lock',          status: r.ssl?.status,     detail: r.ssl?.grade ? `Grade ${r.ssl.grade}` : undefined },
        { key: 'headers', label: 'Headers HTTP',      icon: 'http',          status: r.headers?.status,  detail: r.headers?.missing_count ? `${r.headers.missing_count} manquants` : undefined },
        { key: 'cookies', label: 'Cookies',           icon: 'cookie',        status: r.cookies?.status },
        { key: 'cors',    label: 'CORS',              icon: 'swap_horiz',    status: r.cors?.status },
        { key: 'email',   label: 'SPF / DKIM / DMARC',icon: 'email',        status: r.email?.status },
        { key: 'cms',     label: 'CMS détecté',       icon: 'web',           status: r.cms?.status,      detail: r.cms?.cms_detected || undefined },
        { key: 'waf',     label: 'Pare-feu (WAF)',    icon: 'security',      status: r.waf?.status,      detail: r.waf?.waf_detected || undefined },
        { key: 'ip',      label: 'Réputation IP',     icon: 'gps_fixed',     status: r.ip?.status },
        { key: 'dns',     label: 'DNS / Sous-domaines',icon: 'dns',          status: r.dns?.status,      detail: r.dns?.total_found ? `${r.dns.total_found} trouvés` : undefined },
      ];
    } catch { return []; }
  }

  moduleIcon(status: string | null): string {
    switch (status) {
      case 'OK': return 'check_circle';
      case 'WARNING': return 'warning';
      case 'CRITICAL': return 'cancel';
      default: return 'help_outline';
    }
  }

  moduleColor(status: string | null): string {
    switch (status) {
      case 'OK': return 'text-green-400';
      case 'WARNING': return 'text-yellow-400';
      case 'CRITICAL': return 'text-red-400';
      default: return 'text-gray-500';
    }
  }
}
