import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink, Router } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { HttpClient } from '@angular/common/http';
import { Subscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import { CyberscanService, PublicScanResult } from '../services/cyberscan.service';
import { AuthService } from '../../../core/services/auth.service';
import { ScoreGaugeComponent } from '../../../shared/score-gauge/score-gauge.component';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { computeScore, getGrade, getScoreColor } from '../../../shared/score-utils';
import { environment } from '../../../../environments/environment';

interface Module {
  key: string;
  label: string;
  icon: string;
  status: string | null;
  detail?: string;
}

@Component({
  standalone: true,
  selector: 'app-scan-gratuit',
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule,
    ScoreGaugeComponent, NavButtonsComponent,
  ],
  templateUrl: './scan-gratuit.component.html',
})
export class ScanGratuitComponent implements OnInit, OnDestroy {
  private cyberscan = inject(CyberscanService);
  private auth = inject(AuthService);
  private http = inject(HttpClient);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private titleService = inject(Title);
  private meta = inject(Meta);

  form = this.fb.nonNullable.group({
    url: ['', [Validators.required, Validators.pattern(/^https?:\/\/.+\..+/)]],
    email: ['', [Validators.email]],
    consent: [false],
  });

  submitting = signal(false);
  scan = signal<PublicScanResult | null>(null);
  emailSent = signal(false);
  error = signal<string | null>(null);
  checkoutLoading = false;

  private pollSub: Subscription | null = null;

  ngOnInit() {
    this.titleService.setTitle('Scan de sécurité gratuit — Audit de votre site en 90 secondes | CyberScan');
    this.meta.updateTag({
      name: 'description',
      content: 'Scannez gratuitement votre site web : SSL, headers de sécurité, réputation IP, configuration DNS. Résultats en 90 secondes. Aucun compte requis.',
    });
  }

  ngOnDestroy() {
    this.pollSub?.unsubscribe();
  }

  get urlInvalid(): boolean {
    const c = this.form.controls.url;
    return c.dirty && c.invalid && !!c.value;
  }

  submit() {
    if (this.form.controls.url.invalid || this.submitting()) return;

    const { url, email, consent } = this.form.getRawValue();
    const trimmedUrl = url.trim();

    this.submitting.set(true);
    this.error.set(null);
    this.scan.set(null);

    this.cyberscan.createPublicScan(trimmedUrl).subscribe({
      next: result => {
        this.submitting.set(false);
        if (email && consent) {
          this.http.post(`${environment.apiUrl}/newsletter/subscribe`, { email })
            .subscribe({ next: () => {}, error: () => {} });
        }
        this.router.navigate(['/cyberscan/demo-result', result.token]);
      },
      error: err => {
        this.submitting.set(false);
        this.error.set(err.error?.detail || 'Erreur lors du lancement du scan. Vérifiez l\'URL.');
      },
    });
  }

  private startPolling(token: string) {
    this.pollSub?.unsubscribe();
    this.pollSub = interval(3000).pipe(
      switchMap(() => this.cyberscan.getPublicScan(token)),
      takeWhile(s => s.status === 'pending' || s.status === 'running', true),
    ).subscribe({
      next: s => this.scan.set(s),
      error: () => this.error.set('Impossible de récupérer les résultats.'),
    });
  }

  openCheckout() {
    if (!this.auth.isAuthenticated()) {
      this.router.navigate(['/cyberscan'], { queryParams: { action: 'register' } });
      return;
    }
    this.checkoutLoading = true;
    this.cyberscan.getPlans().subscribe({
      next: plans => {
        if (!plans.length) { this.checkoutLoading = false; return; }
        const starter = plans.reduce((a, b) => a.price_eur < b.price_eur ? a : b);
        this.cyberscan.createCheckout(starter.id).subscribe({
          next: res => { window.location.href = res.checkout_url; },
          error: () => { this.checkoutLoading = false; },
        });
      },
      error: () => { this.checkoutLoading = false; },
    });
  }

  resetScan() {
    this.pollSub?.unsubscribe();
    this.scan.set(null);
    this.error.set(null);
    this.form.reset();
  }

  get isRunning(): boolean {
    const s = this.scan()?.status;
    return s === 'pending' || s === 'running';
  }

  get score(): number | null {
    return computeScore(this.scan()?.results_json ?? null);
  }

  getGrade(s: number) { return getGrade(s); }
  getScoreColor(s: number) { return getScoreColor(s); }

  get modules(): Module[] {
    const json = this.scan()?.results_json;
    if (!json) return [];
    try {
      const r = JSON.parse(json);
      return [
        { key: 'ssl',     label: 'Certificat SSL',        icon: 'lock',       status: r.ssl?.status,     detail: r.ssl?.grade ? `Grade ${r.ssl.grade}` : undefined },
        { key: 'headers', label: 'Headers HTTP',           icon: 'http',       status: r.headers?.status,  detail: r.headers?.missing_count ? `${r.headers.missing_count} manquants` : undefined },
        { key: 'cookies', label: 'Cookies',                icon: 'cookie',     status: r.cookies?.status },
        { key: 'cors',    label: 'CORS',                   icon: 'swap_horiz', status: r.cors?.status },
        { key: 'email',   label: 'SPF / DKIM / DMARC',    icon: 'email',      status: r.email?.status },
        { key: 'cms',     label: 'CMS / Technologies',     icon: 'web',        status: r.cms?.status,      detail: r.cms?.cms_detected || undefined },
        { key: 'waf',     label: 'Pare-feu (WAF)',         icon: 'security',   status: r.waf?.status },
        { key: 'ip',      label: 'Réputation IP',          icon: 'gps_fixed',  status: r.ip?.status },
        { key: 'dns',     label: 'DNS',                    icon: 'dns',        status: r.dns?.status },
      ];
    } catch { return []; }
  }

  moduleIcon(status: string | null): string {
    switch (status) {
      case 'OK':       return 'check_circle';
      case 'WARNING':  return 'warning';
      case 'CRITICAL': return 'cancel';
      default:         return 'help_outline';
    }
  }

  moduleColor(status: string | null): string {
    switch (status) {
      case 'OK':       return 'text-green-400';
      case 'WARNING':  return 'text-yellow-400';
      case 'CRITICAL': return 'text-red-400';
      default:         return 'text-gray-500';
    }
  }

  get criticalCount(): number {
    return this.modules.filter(m => m.status === 'CRITICAL').length;
  }

  get warningCount(): number {
    return this.modules.filter(m => m.status === 'WARNING').length;
  }
}
