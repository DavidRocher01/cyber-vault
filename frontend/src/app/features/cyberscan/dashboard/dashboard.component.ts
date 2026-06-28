import {
  Component,
  DestroyRef,
  inject,
  OnInit,
  OnDestroy,
  signal,
  HostListener,
  ElementRef,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink, ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { Title, Meta } from '@angular/platform-browser';
import { EMPTY, Subscription as RxSubscription, interval, switchMap, tap } from 'rxjs';
import { pollWithBackoff } from '../../../shared/poll-with-backoff';

import {
  CyberscanService,
  Site,
  Scan,
  Subscription as UserSubscription,
  Plan,
  AppNotification,
} from '../services/cyberscan.service';
import { AuthService } from '../../../core/services/auth.service';
import { SkeletonComponent } from '../../../shared/skeleton/skeleton.component';
import { ConfirmDialogComponent } from '../../../shared/confirm-dialog/confirm-dialog.component';
import { ThemeService } from '../../../core/services/theme.service';
import { I18nService } from '../../../core/services/i18n.service';
import {
  computeScore,
  getGrade,
  getScoreColor,
  getCategoryScores,
  RADAR_CATEGORIES,
} from '../../../shared/score-utils';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { environment } from '../../../../environments/environment';
import { StatsCardsComponent } from './components/stats-cards/stats-cards.component';
import { RecentScansComponent } from './components/recent-scans/recent-scans.component';
import { SitesGridComponent } from './components/sites-grid/sites-grid.component';

type ScanFilter = 'all' | 'done' | 'running' | 'error';

interface PaginatedScans {
  items: Scan[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

@Component({
  standalone: true,
  selector: 'app-cyberscan-dashboard',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatSnackBarModule,
    MatDialogModule,
    MatPaginatorModule,
    SkeletonComponent,
    NavButtonsComponent,
    StatsCardsComponent,
    RecentScansComponent,
    SitesGridComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit, OnDestroy {
  private cyberscan = inject(CyberscanService);
  private authService = inject(AuthService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private dialog = inject(MatDialog);
  private titleService = inject(Title);
  private meta = inject(Meta);
  private el = inject(ElementRef);
  private destroyRef = inject(DestroyRef);
  private pollingMap: Record<number, RxSubscription> = {};

  readonly theme = inject(ThemeService).theme;
  readonly i18n = inject(I18nService);
  readonly version = environment.version;

  subscription = signal<UserSubscription | null>(null);
  sites = signal<Site[]>([]);
  scansMap = signal<Record<number, PaginatedScans>>({});
  loadingScans = signal<Record<number, boolean>>({});
  triggeringScans = signal<Record<number, boolean>>({});
  scanFilter = signal<ScanFilter>('all');
  pageMap = signal<Record<number, number>>({});

  loading = signal(true);
  addingSite = signal(false);
  showAddForm = signal(false);

  // Plans modal
  showPlansModal = signal(false);
  plans = signal<Plan[]>([]);
  checkoutLoading = signal<number | null>(null);

  // Notifications
  notifications = signal<AppNotification[]>([]);
  unreadCount = signal(0);
  showNotifPanel = signal(false);

  siteForm = this.fb.nonNullable.group({
    url: ['', [Validators.required, Validators.pattern(/^https?:\/\/.+/)]],
    name: ['', Validators.required],
  });

  ngOnInit() {
    this.titleService.setTitle('Dashboard — Rocher Cybersécurité');
    this.meta.updateTag({
      name: 'description',
      content: 'Gérez vos sites et consultez vos rapports de sécurité Rocher Cybersécurité.',
    });

    this.route.queryParams.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(params => {
      if (params['subscribed'] === 'true') {
        this.snack.open('Abonnement activé ! Bienvenue sur Rocher Cybersécurité.', 'Super', {
          duration: 6000,
        });
      }
      if (params['upgrade'] === 'true') {
        this.openPlansModal();
      }
    });
    this.loadDashboard();
  }

  ngOnDestroy() {
    Object.values(this.pollingMap).forEach(sub => sub.unsubscribe());
  }

  logout() {
    this.authService.logout();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    if (
      this.showNotifPanel() &&
      !this.el.nativeElement.querySelector('.notif-panel-anchor')?.contains(event.target)
    ) {
      this.showNotifPanel.set(false);
    }
  }

  loadDashboard() {
    this.loading.set(true);
    this.cyberscan
      .getMySubscription()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        tap(sub => this.subscription.set(sub)),
        switchMap(sub => {
          if (!sub) {
            this.loading.set(false);
            this.router.navigate(['/onboarding']);
            return EMPTY;
          }
          return this.cyberscan.getMySites();
        })
      )
      .subscribe({
        next: sites => {
          this.sites.set(sites);
          this.loading.set(false);
          sites.forEach(s => this.loadScans(s.id, 1));
        },
        error: () => this.loading.set(false),
      });
    this.loadNotifications();
    interval(30000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.loadNotifications());
  }

  loadNotifications() {
    this.cyberscan.getNotifications().subscribe({
      next: data => {
        this.notifications.set(data.items);
        this.unreadCount.set(data.unread_count);
      },
      error: () => {},
    });
  }

  toggleNotifPanel(event: MouseEvent) {
    event.stopPropagation();
    this.showNotifPanel.update(v => !v);
  }

  handleNotifClick(notif: AppNotification) {
    if (!notif.read) {
      this.cyberscan.markNotificationRead(notif.id).subscribe({
        next: updated => {
          this.notifications.update(list => list.map(n => (n.id === notif.id ? updated : n)));
          this.unreadCount.update(c => Math.max(0, c - 1));
        },
        error: () => {},
      });
    }
    if (notif.link) {
      this.router.navigateByUrl(notif.link);
      this.showNotifPanel.set(false);
    }
  }

  markAllRead() {
    this.cyberscan.markAllNotificationsRead().subscribe({
      next: () => {
        this.notifications.update(list => list.map(n => ({ ...n, read: true })));
        this.unreadCount.set(0);
      },
      error: () => {},
    });
  }

  dismissNotif(event: MouseEvent, id: number) {
    event.stopPropagation();
    this.cyberscan.deleteNotification(id).subscribe({
      next: () => {
        const notif = this.notifications().find(n => n.id === id);
        this.notifications.update(list => list.filter(n => n.id !== id));
        if (notif && !notif.read) this.unreadCount.update(c => Math.max(0, c - 1));
      },
      error: () => {},
    });
  }

  loadScans(siteId: number, page: number) {
    this.loadingScans.update(m => ({ ...m, [siteId]: true }));
    this.pageMap.update(m => ({ ...m, [siteId]: page }));
    this.cyberscan.getSiteScans(siteId, page).subscribe({
      next: data => {
        this.scansMap.update(m => ({ ...m, [siteId]: data }));
        this.loadingScans.update(m => ({ ...m, [siteId]: false }));
        this.maybeStartPolling(siteId, data.items);
      },
      error: () => this.loadingScans.update(m => ({ ...m, [siteId]: false })),
    });
  }

  onPageChange(siteId: number, event: PageEvent) {
    this.loadScans(siteId, event.pageIndex + 1);
  }

  maybeStartPolling(siteId: number, scans: Scan[]) {
    const hasActive = scans.some(s => s.status === 'pending' || s.status === 'running');
    if (!hasActive || this.pollingMap[siteId]) return;
    this.forceStartPolling(siteId);
  }

  /** Start polling unconditionally (used after triggering a new scan). */
  private forceStartPolling(siteId: number) {
    this.pollingMap[siteId]?.unsubscribe();
    this.pollingMap[siteId] = pollWithBackoff(
      () => this.cyberscan.getSiteScans(siteId, this.pageMap()[siteId] ?? 1),
      d => !d.items.some(x => x.status === 'pending' || x.status === 'running')
    ).subscribe(data => {
      this.scansMap.update(m => ({ ...m, [siteId]: data }));
      if (!data.items.some(s => s.status === 'pending' || s.status === 'running'))
        delete this.pollingMap[siteId];
    });
  }

  autoPrependHttps() {
    const ctrl = this.siteForm.controls.url;
    const v = ctrl.value.trim();
    if (v && !v.startsWith('http://') && !v.startsWith('https://')) {
      ctrl.setValue('https://' + v, { emitEvent: true });
      ctrl.markAsTouched();
    }
  }

  addSite() {
    if (this.siteForm.invalid) return;
    this.addingSite.set(true);
    this.cyberscan.createSite(this.siteForm.getRawValue()).subscribe({
      next: site => {
        this.sites.update(s => [...s, site]);
        this.siteForm.reset();
        this.showAddForm.set(false);
        this.addingSite.set(false);
        this.snack.open('Site ajouté', 'OK', { duration: 3000 });
        this.loadScans(site.id, 1);
      },
      error: err => {
        this.addingSite.set(false);
        this.snack.open(err.error?.detail || "Erreur lors de l'ajout", 'Fermer', {
          duration: 5000,
        });
      },
    });
  }

  confirmDeleteSite(site: Site) {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Supprimer le site',
        message: `Supprimer "${site.name}" et tout son historique de scans ?`,
        confirm: 'Supprimer',
        danger: true,
      },
      panelClass: 'dark-dialog',
    });
    ref.afterClosed().subscribe(ok => {
      if (!ok) return;
      this.cyberscan.deleteSite(site.id).subscribe({
        next: () => {
          this.sites.update(s => s.filter(x => x.id !== site.id));
          this.snack.open('Site supprimé', 'OK', { duration: 3000 });
        },
      });
    });
  }

  triggerScan(siteId: number) {
    this.triggeringScans.update(m => ({ ...m, [siteId]: true }));
    this.cyberscan.triggerScan(siteId).subscribe({
      next: () => {
        this.triggeringScans.update(m => ({ ...m, [siteId]: false }));
        this.snack.open('Scan lancé — mise à jour automatique en cours', 'OK', { duration: 5000 });
        this.loadScans(siteId, 1);
        // Force polling regardless of what loadScans returns — covers the race condition
        // where the scan finishes before the GET response arrives (hasActive = false).
        this.forceStartPolling(siteId);
      },
      error: err => {
        this.triggeringScans.update(m => ({ ...m, [siteId]: false }));
        this.snack.open(err.error?.detail || 'Erreur lors du lancement', 'Fermer', {
          duration: 5000,
        });
      },
    });
  }

  openPlansModal() {
    this.showPlansModal.set(true);
    if (this.plans().length === 0) {
      this.cyberscan.getPlans().subscribe({ next: p => this.plans.set(p) });
    }
  }

  selectPlan(plan: Plan) {
    this.checkoutLoading.set(plan.id);
    this.cyberscan.invalidateSubscriptionCache();
    this.cyberscan.createCheckout(plan.id).subscribe({
      next: res => {
        const url = res.checkout_url;
        try {
          const parsed = new URL(url);
          if (parsed.hostname === window.location.hostname) {
            this.router.navigateByUrl(parsed.pathname + parsed.search);
          } else if (parsed.hostname === 'checkout.stripe.com') {
            window.location.href = url;
          }
        } catch {
          if (url.startsWith('/')) this.router.navigateByUrl(url);
        }
      },
      error: () => this.checkoutLoading.set(null),
    });
  }

  openBillingPortal() {
    this.cyberscan.getBillingPortal().subscribe({
      next: res => {
        try {
          const parsed = new URL(res.checkout_url);
          if (
            parsed.hostname === 'billing.stripe.com' ||
            parsed.hostname === 'checkout.stripe.com'
          ) {
            window.location.href = res.checkout_url;
          }
        } catch {
          /* URL invalide ignorée */
        }
      },
    });
  }

  formatPrice(cents: number): string {
    return (cents / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
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
      error: () =>
        this.snack.open('Erreur lors du téléchargement du PDF', 'Fermer', { duration: 4000 }),
    });
  }

  getScans(siteId: number): Scan[] {
    const all = this.scansMap()[siteId]?.items || [];
    const f = this.scanFilter();
    if (f === 'all') return all;
    if (f === 'running') return all.filter(s => s.status === 'pending' || s.status === 'running');
    return all.filter(s => s.status === f);
  }

  getTotal(siteId: number): number {
    return this.scansMap()[siteId]?.total ?? 0;
  }
  getPerPage(siteId: number): number {
    return this.scansMap()[siteId]?.per_page ?? 10;
  }
  getCurrentPage(siteId: number): number {
    return (this.scansMap()[siteId]?.page ?? 1) - 1;
  }
  isLoadingScans(siteId: number): boolean {
    return this.loadingScans()[siteId] || false;
  }
  isTriggeringScans(siteId: number): boolean {
    return this.triggeringScans()[siteId] || false;
  }
  hasActiveScans(siteId: number): boolean {
    return (this.scansMap()[siteId]?.items || []).some(
      s => s.status === 'pending' || s.status === 'running'
    );
  }
  lastScanStatus(siteId: number): string | null {
    return (this.scansMap()[siteId]?.items || [])[0]?.overall_status ?? null;
  }

  siteBadgeClass(siteId: number): string {
    if (this.hasActiveScans(siteId)) return 'bg-blue-500/20 text-blue-300 border-blue-600';
    switch (this.lastScanStatus(siteId)) {
      case 'OK':
        return 'bg-green-500/20 text-green-300 border-green-600';
      case 'WARNING':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-600';
      case 'CRITICAL':
        return 'bg-red-500/20 text-red-300 border-red-600';
      default:
        return 'bg-gray-700 text-gray-400 border-gray-600';
    }
  }

  siteBadgeLabel(siteId: number): string {
    if (this.hasActiveScans(siteId)) return 'En cours...';
    return this.lastScanStatus(siteId) ?? 'Aucun scan';
  }

  siteBadgeIcon(siteId: number): string {
    if (this.hasActiveScans(siteId)) return 'sync';
    switch (this.lastScanStatus(siteId)) {
      case 'OK':
        return 'verified_user';
      case 'WARNING':
        return 'warning';
      case 'CRITICAL':
        return 'gpp_bad';
      default:
        return 'help_outline';
    }
  }

  statusColor(s: string | null): string {
    switch (s) {
      case 'OK':
        return 'text-green-400';
      case 'WARNING':
        return 'text-yellow-400';
      case 'CRITICAL':
      case 'error':
        return 'text-red-400';
      case 'done':
        return 'text-green-400';
      case 'pending':
      case 'running':
        return 'text-blue-400';
      default:
        return 'text-gray-400';
    }
  }

  statusIcon(s: string | null): string {
    switch (s) {
      case 'OK':
        return 'verified_user';
      case 'WARNING':
        return 'warning';
      case 'CRITICAL':
        return 'gpp_bad';
      case 'done':
        return 'check_circle';
      case 'pending':
        return 'schedule';
      case 'running':
        return 'sync';
      case 'error':
        return 'cancel';
      default:
        return 'help_outline';
    }
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  get maxSites(): number {
    return this.subscription()?.plan?.max_sites ?? 0;
  }
  get effectiveMaxSites(): number {
    const sub = this.subscription();
    return (sub?.plan?.max_sites ?? 0) + (sub?.extra_sites ?? 0);
  }
  get canAddSite(): boolean {
    return this.sites().length < this.effectiveMaxSites;
  }

  buyingExtraSites = signal(false);

  purchaseExtraSites() {
    this.buyingExtraSites.set(true);
    this.cyberscan.purchaseExtraSites().subscribe({
      next: res => {
        this.buyingExtraSites.set(false);
        try {
          const parsed = new URL(res.checkout_url);
          if (parsed.hostname === 'checkout.stripe.com') {
            window.location.href = res.checkout_url;
          } else {
            this.router.navigateByUrl(parsed.pathname + parsed.search);
          }
        } catch {
          if (res.checkout_url.startsWith('/')) this.router.navigateByUrl(res.checkout_url);
        }
      },
      error: () => {
        this.buyingExtraSites.set(false);
        this.snack.open("Erreur lors de l'achat", 'Fermer', { duration: 4000 });
      },
    });
  }

  // --- Score & trend ---
  getScanScore(scan: Scan): number | null {
    return computeScore(scan.results_json ?? null);
  }

  getLastScore(siteId: number): number | null {
    const done = (this.scansMap()[siteId]?.items ?? []).find(
      s => s.status === 'done' && s.results_json
    );
    return done ? computeScore(done.results_json ?? null) : null;
  }

  getPrevScore(siteId: number): number | null {
    const done = (this.scansMap()[siteId]?.items ?? []).filter(
      s => s.status === 'done' && s.results_json
    );
    return done.length >= 2 ? computeScore(done[1].results_json ?? null) : null;
  }

  getTrend(siteId: number): number | null {
    const last = this.getLastScore(siteId);
    const prev = this.getPrevScore(siteId);
    if (last === null || prev === null) return null;
    return last - prev;
  }

  getGrade(score: number): string {
    return getGrade(score);
  }
  getScoreColor(score: number): string {
    return getScoreColor(score);
  }

  // ── Analytics ─────────────────────────────────────────────────────────────

  /** Average delta of last-vs-prev score across all sites with at least 2 scans */
  get globalTrend(): number | null {
    const deltas = this.sites()
      .map(s => this.getTrend(s.id))
      .filter((t): t is number => t !== null);
    if (deltas.length === 0) return null;
    return Math.round(deltas.reduce((a, b) => a + b, 0) / deltas.length);
  }

  get globalTrendAnnotation(): string | null {
    const score = this.averageScore;
    if (score === null) return null;
    const trend = this.globalTrend;
    if (trend === null) return `Score global : ${score}/100`;
    if (Math.abs(trend) < 2) return `Score stable à ${score}/100 depuis le dernier scan`;
    if (trend > 0) return `+${trend} pts depuis le dernier scan — score global : ${score}/100`;
    return `${trend} pts depuis le dernier scan — score global : ${score}/100`;
  }

  /** All score/date points from all sites merged and sorted by date (for global chart) */
  get globalScoreTimeline(): { date: string; score: number }[] {
    const all: { date: string; score: number }[] = [];
    for (const site of this.sites()) {
      for (const pt of this.scoreHistory(site.id, 8)) {
        all.push(pt);
      }
    }
    return all.sort((a, b) => a.date.localeCompare(b.date)).slice(-16);
  }

  private _trendGeometry(w = 360, h = 56): { points: string; dots: { cx: number; cy: number }[] } {
    const history = this.globalScoreTimeline;
    if (history.length < 2) return { points: '', dots: [] };
    const min = Math.min(...history.map(p => p.score));
    const max = Math.max(...history.map(p => p.score));
    const range = max - min || 1;
    const xs = history.map((_, i) => (i / (history.length - 1)) * w);
    const ys = history.map(p => h - ((p.score - min) / range) * (h - 8) - 4);
    return {
      points: xs.map((x, i) => `${x.toFixed(1)},${ys[i].toFixed(1)}`).join(' '),
      dots: xs.map((cx, i) => ({ cx, cy: ys[i] })),
    };
  }

  globalTrendChartPoints(w = 360, h = 56): string {
    return this._trendGeometry(w, h).points;
  }

  get globalTrendDots(): { cx: number; cy: number }[] {
    return this._trendGeometry().dots;
  }

  get globalTrendIsStable(): boolean {
    return Math.abs(this.globalTrend ?? 0) <= 1;
  }

  analyticsOpen = signal(true);
  toggleAnalytics() {
    this.analyticsOpen.update(v => !v);
  }
  readonly categoryLabels = RADAR_CATEGORIES.map(c => c.label);

  /** Last N done scans with a score, for sparkline */
  scoreHistory(siteId: number, n = 8): { score: number; date: string }[] {
    return (this.scansMap()[siteId]?.items ?? [])
      .filter(s => s.status === 'done' && s.results_json)
      .slice(0, n)
      .reverse()
      .map(s => ({ score: computeScore(s.results_json ?? null) ?? 0, date: s.created_at ?? '' }));
  }

  /** SVG polyline points for a sparkline, normalized to [0, height] */
  sparklinePoints(siteId: number, w = 120, h = 32): string {
    const history = this.scoreHistory(siteId);
    if (history.length < 2) return '';
    const xs = history.map((_, i) => (i / (history.length - 1)) * w);
    const min = Math.min(...history.map(p => p.score));
    const max = Math.max(...history.map(p => p.score));
    const range = max - min || 1;
    const ys = history.map(p => h - ((p.score - min) / range) * (h - 4) - 2);
    return xs.map((x, i) => `${x.toFixed(1)},${ys[i].toFixed(1)}`).join(' ');
  }

  /** Average category scores across all sites (from last done scan per site) */
  get globalCategoryScores(): { label: string; score: number }[] {
    const perSite = this.sites()
      .map(s => {
        const scan = (this.scansMap()[s.id]?.items ?? []).find(
          x => x.status === 'done' && x.results_json
        );
        return scan ? getCategoryScores(scan.results_json ?? null) : null;
      })
      .filter((v): v is number[] => v !== null);

    if (perSite.length === 0) return [];
    return RADAR_CATEGORIES.map((cat, i) => ({
      label: cat.label,
      score: Math.round(perSite.reduce((sum, s) => sum + s[i], 0) / perSite.length),
    }));
  }

  get criticalCount(): number {
    return this.sites().filter(s => this.lastScanStatus(s.id) === 'CRITICAL').length;
  }

  get warningCount(): number {
    return this.sites().filter(s => this.lastScanStatus(s.id) === 'WARNING').length;
  }

  getSslDaysRemaining(siteId: number): number | null {
    const scan = (this.scansMap()[siteId]?.items ?? []).find(
      s => s.status === 'done' && s.results_json
    );
    if (!scan?.results_json) return null;
    try {
      return JSON.parse(scan.results_json)?.ssl?.days_remaining ?? null;
    } catch {
      return null;
    }
  }

  get okCount(): number {
    return this.sites().filter(s => this.lastScanStatus(s.id) === 'OK').length;
  }

  get totalScans(): number {
    return Object.values(this.scansMap()).reduce((sum, p) => sum + (p?.total ?? 0), 0);
  }

  // ── Builder helpers for SitesGridComponent @Input() maps ─────────────────

  buildLastScores(): Record<number, number | null> {
    const result: Record<number, number | null> = {};
    for (const site of this.sites()) result[site.id] = this.getLastScore(site.id);
    return result;
  }

  buildTrends(): Record<number, number | null> {
    const result: Record<number, number | null> = {};
    for (const site of this.sites()) result[site.id] = this.getTrend(site.id);
    return result;
  }

  buildSslDays(): Record<number, number | null> {
    const result: Record<number, number | null> = {};
    for (const site of this.sites()) result[site.id] = this.getSslDaysRemaining(site.id);
    return result;
  }

  buildActiveScansMap(): Record<number, boolean> {
    const result: Record<number, boolean> = {};
    for (const site of this.sites()) result[site.id] = this.hasActiveScans(site.id);
    return result;
  }

  buildLastScanStatuses(): Record<number, string | null> {
    const result: Record<number, string | null> = {};
    for (const site of this.sites()) result[site.id] = this.lastScanStatus(site.id);
    return result;
  }

  get averageScore(): number | null {
    const scores = this.sites()
      .map(s => this.getLastScore(s.id))
      .filter((s): s is number => s !== null);
    if (scores.length === 0) return null;
    return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  }
}
