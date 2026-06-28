import { Component, inject, OnInit, OnDestroy, signal, DOCUMENT } from '@angular/core';
import { RouterLink, ActivatedRoute, Router } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Subscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import { CyberscanService, PublicScanResult } from '../services/cyberscan.service';
import { AuthService } from '../../../core/services/auth.service';
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
  imports: [
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    ScoreGaugeComponent,
    NavButtonsComponent,
  ],
  templateUrl: './demo-result.component.html',
})
export class DemoResultComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private cyberscan = inject(CyberscanService);
  private auth = inject(AuthService);
  private titleService = inject(Title);
  private metaService = inject(Meta);
  private document = inject(DOCUMENT);

  scan = signal<PublicScanResult | null>(null);
  loading = signal(true);
  error = signal<string | null>(null);
  linkCopied = signal(false);
  checkoutLoading = false;

  private pollSub: Subscription | null = null;

  ngOnInit() {
    const token = this.route.snapshot.paramMap.get('token');
    if (!token) {
      this.router.navigate(['/cyberscan']);
      return;
    }

    this.pollSub = interval(3000)
      .pipe(
        switchMap(() => this.cyberscan.getPublicScan(token)),
        takeWhile(s => s.status === 'pending' || s.status === 'running', true)
      )
      .subscribe({
        next: s => {
          this.scan.set(s);
          this.loading.set(false);
          this._updateMeta(s);
        },
        error: () => {
          this.error.set('Scan introuvable ou expiré.');
          this.loading.set(false);
        },
      });

    this.cyberscan.getPublicScan(token).subscribe({
      next: s => {
        this.scan.set(s);
        this.loading.set(false);
        this._updateMeta(s);
      },
      error: () => {
        this.error.set('Scan introuvable.');
        this.loading.set(false);
      },
    });
  }

  ngOnDestroy() {
    this.pollSub?.unsubscribe();
  }

  openCheckout() {
    if (!this.auth.isAuthenticated()) {
      this.router.navigate(['/cyberscan'], { queryParams: { action: 'register' } });
      return;
    }
    this.checkoutLoading = true;
    this.cyberscan.getPlans().subscribe({
      next: plans => {
        if (!plans.length) {
          this.checkoutLoading = false;
          return;
        }
        const starter = plans.reduce((a, b) => (a.price_eur < b.price_eur ? a : b));
        this.cyberscan.createCheckout(starter.id).subscribe({
          next: res => {
            window.location.href = res.checkout_url;
          },
          error: () => {
            this.checkoutLoading = false;
          },
        });
      },
      error: () => {
        this.checkoutLoading = false;
      },
    });
  }

  private _updateMeta(s: PublicScanResult) {
    if (s.status !== 'done') return;
    const url = this.targetUrl;
    const sc = this.score;
    const title =
      sc !== null
        ? `Rapport de sécurité ${url} — Score ${sc}/100 | Rocher Cybersécurité`
        : `Rapport de sécurité ${url} | Rocher Cybersécurité`;
    this.titleService.setTitle(title);
    this.metaService.updateTag({ property: 'og:title', content: title });
    this.metaService.updateTag({
      property: 'og:description',
      content: `Analyse de sécurité complète de ${url} : SSL, headers, DNS, CORS, réputation IP. Score ${sc}/100.`,
    });
    this.metaService.updateTag({ property: 'og:url', content: this.shareUrl });
  }

  copyLink() {
    this.document.defaultView?.navigator.clipboard.writeText(this.shareUrl).then(() => {
      this.linkCopied.set(true);
      setTimeout(() => this.linkCopied.set(false), 2500);
    });
  }

  get targetUrl(): string {
    const json = this.scan()?.results_json;
    if (!json) return '';
    try {
      return JSON.parse(json)?._meta?.url ?? '';
    } catch {
      return '';
    }
  }

  get shareUrl(): string {
    return this.document.defaultView?.location.href ?? '';
  }

  get score(): number | null {
    return computeScore(this.scan()?.results_json ?? null);
  }
  getGrade(s: number) {
    return getGrade(s);
  }
  getScoreColor(s: number) {
    return getScoreColor(s);
  }

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
        {
          key: 'ssl',
          label: 'Certificat SSL',
          icon: 'lock',
          status: r.ssl?.status,
          detail: r.ssl?.grade ? `Grade ${r.ssl.grade}` : undefined,
        },
        {
          key: 'headers',
          label: 'Headers HTTP',
          icon: 'http',
          status: r.headers?.status,
          detail: r.headers?.missing_count ? `${r.headers.missing_count} manquants` : undefined,
        },
        { key: 'cookies', label: 'Cookies', icon: 'cookie', status: r.cookies?.status },
        { key: 'cors', label: 'CORS', icon: 'swap_horiz', status: r.cors?.status },
        { key: 'email', label: 'SPF / DKIM / DMARC', icon: 'email', status: r.email?.status },
        {
          key: 'cms',
          label: 'CMS détecté',
          icon: 'web',
          status: r.cms?.status,
          detail: r.cms?.cms_detected || undefined,
        },
        {
          key: 'waf',
          label: 'Pare-feu (WAF)',
          icon: 'security',
          status: r.waf?.status,
          detail: r.waf?.waf_detected || undefined,
        },
        { key: 'ip', label: 'Réputation IP', icon: 'gps_fixed', status: r.ip?.status },
        {
          key: 'dns',
          label: 'DNS / Sous-domaines',
          icon: 'dns',
          status: r.dns?.status,
          detail: r.dns?.total_found ? `${r.dns.total_found} trouvés` : undefined,
        },
      ];
    } catch {
      return [];
    }
  }

  moduleIcon(status: string | null): string {
    switch (status) {
      case 'OK':
        return 'check_circle';
      case 'WARNING':
        return 'warning';
      case 'CRITICAL':
        return 'cancel';
      default:
        return 'help_outline';
    }
  }

  moduleColor(status: string | null): string {
    switch (status) {
      case 'OK':
        return 'text-green-400';
      case 'WARNING':
        return 'text-yellow-400';
      case 'CRITICAL':
        return 'text-red-400';
      default:
        return 'text-gray-500';
    }
  }
}
