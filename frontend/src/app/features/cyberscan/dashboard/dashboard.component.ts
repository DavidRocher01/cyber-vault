import { Component, inject, OnInit, OnDestroy, signal, HostListener, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink, ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { Title, Meta } from '@angular/platform-browser';
import { Subscription as RxSubscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import { CyberscanService, Site, Scan, Subscription as UserSubscription, Plan, AppNotification } from '../services/cyberscan.service';
import { SkeletonComponent } from '../../../shared/skeleton/skeleton.component';
import { ConfirmDialogComponent } from '../../../shared/confirm-dialog/confirm-dialog.component';
import { ThemeService } from '../../../core/services/theme.service';
import { I18nService } from '../../../core/services/i18n.service';
import { ScoreGaugeComponent } from '../../../shared/score-gauge/score-gauge.component';
import { computeScore, getGrade, getScoreColor } from '../../../shared/score-utils';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

type ScanFilter = 'all' | 'done' | 'running' | 'error';

interface PaginatedScans {
  items: Scan[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

@Component({
  selector: 'app-cyberscan-dashboard',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatButtonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule,
    MatFormFieldModule, MatInputModule, MatChipsModule, MatSnackBarModule,
    MatDialogModule, MatPaginatorModule, SkeletonComponent, ScoreGaugeComponent, NavButtonsComponent,
  ],
  templateUrl: './dashboard.component.html',
})
export class DashboardComponent implements OnInit, OnDestroy {
  private cyberscan = inject(CyberscanService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private dialog = inject(MatDialog);
  private titleService = inject(Title);
  private meta = inject(Meta);
  private el = inject(ElementRef);
  private pollingMap: Record<number, RxSubscription> = {};
  private notifPollSub: RxSubscription | null = null;

  readonly theme = inject(ThemeService).theme;
  readonly i18n = inject(I18nService);

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
    this.titleService.setTitle('Dashboard — CyberScan');
    this.meta.updateTag({ name: 'description', content: 'Gérez vos sites et consultez vos rapports de sécurité CyberScan.' });

    this.route.queryParams.subscribe(params => {
      if (params['subscribed'] === 'true') {
        this.snack.open('Abonnement activé ! Bienvenue sur CyberScan.', 'Super', { duration: 6000 });
      }
    });
    this.loadDashboard();
  }

  ngOnDestroy() {
    Object.values(this.pollingMap).forEach(sub => sub.unsubscribe());
    this.notifPollSub?.unsubscribe();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    if (this.showNotifPanel() && !this.el.nativeElement.querySelector('.notif-panel-anchor')?.contains(event.target)) {
      this.showNotifPanel.set(false);
    }
  }

  loadDashboard() {
    this.loading.set(true);
    this.cyberscan.getMySubscription().subscribe({
      next: sub => {
        this.subscription.set(sub);
        if (!sub) {
          // No subscription: check sites first
          this.cyberscan.getMySites().subscribe({
            next: sites => {
              this.sites.set(sites);
              this.loading.set(false);
              if (sites.length === 0) {
                this.router.navigate(['/cyberscan/onboarding']);
                return;
              }
              sites.forEach(s => this.loadScans(s.id, 1));
            },
            error: () => this.loading.set(false),
          });
          return;
        }
        this.cyberscan.getMySites().subscribe({
          next: sites => {
            this.sites.set(sites);
            this.loading.set(false);
            sites.forEach(s => this.loadScans(s.id, 1));
          },
          error: () => this.loading.set(false),
        });
      },
      error: () => this.loading.set(false),
    });
    this.loadNotifications();
    // Poll notifications every 30s
    this.notifPollSub = interval(30000).subscribe(() => this.loadNotifications());
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
          this.notifications.update(list => list.map(n => n.id === notif.id ? updated : n));
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
    this.pollingMap[siteId] = interval(4000).pipe(
      switchMap(() => this.cyberscan.getSiteScans(siteId, this.pageMap()[siteId] ?? 1)),
      takeWhile(d => d.items.some(x => x.status === 'pending' || x.status === 'running'), true),
    ).subscribe(data => {
      this.scansMap.update(m => ({ ...m, [siteId]: data }));
      if (!data.items.some(s => s.status === 'pending' || s.status === 'running')) delete this.pollingMap[siteId];
    });
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
        this.snack.open(err.error?.detail || "Erreur lors de l'ajout", 'Fermer', { duration: 5000 });
      },
    });
  }

  confirmDeleteSite(site: Site) {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      data: { title: 'Supprimer le site', message: `Supprimer "${site.name}" et tout son historique de scans ?`, confirm: 'Supprimer', danger: true },
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
      },
      error: err => {
        this.triggeringScans.update(m => ({ ...m, [siteId]: false }));
        this.snack.open(err.error?.detail || 'Erreur lors du lancement', 'Fermer', { duration: 5000 });
      },
    });
  }

  exportCsv(siteId: number) {
    window.open(this.cyberscan.exportCsv(siteId), '_blank');
  }

  openPlansModal() {
    this.showPlansModal.set(true);
    if (this.plans().length === 0) {
      this.cyberscan.getPlans().subscribe({ next: p => this.plans.set(p) });
    }
  }

  selectPlan(plan: Plan) {
    this.checkoutLoading.set(plan.id);
    this.cyberscan.createCheckout(plan.id).subscribe({
      next: res => {
        const url = res.checkout_url;
        // Internal route (dev mode) → use Angular router to preserve nav history
        if (url.startsWith('/') || url.includes(window.location.host)) {
          const path = url.startsWith('/') ? url : new URL(url).pathname;
          this.router.navigateByUrl(path);
        } else {
          window.location.href = url;
        }
      },
      error: () => this.checkoutLoading.set(null),
    });
  }

  openBillingPortal() {
    this.cyberscan.getBillingPortal().subscribe({ next: res => window.location.href = res.checkout_url });
  }

  formatPrice(cents: number): string {
    return (cents / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
  }

  downloadPdf(scanId: number) {
    window.open(this.cyberscan.downloadPdf(scanId), '_blank');
  }

  getScans(siteId: number): Scan[] {
    const all = this.scansMap()[siteId]?.items || [];
    const f = this.scanFilter();
    if (f === 'all') return all;
    if (f === 'running') return all.filter(s => s.status === 'pending' || s.status === 'running');
    return all.filter(s => s.status === f);
  }

  getTotal(siteId: number): number { return this.scansMap()[siteId]?.total ?? 0; }
  getPerPage(siteId: number): number { return this.scansMap()[siteId]?.per_page ?? 10; }
  getCurrentPage(siteId: number): number { return (this.scansMap()[siteId]?.page ?? 1) - 1; }
  isLoadingScans(siteId: number): boolean { return this.loadingScans()[siteId] || false; }
  isTriggeringScans(siteId: number): boolean { return this.triggeringScans()[siteId] || false; }
  hasActiveScans(siteId: number): boolean { return (this.scansMap()[siteId]?.items || []).some(s => s.status === 'pending' || s.status === 'running'); }
  lastScanStatus(siteId: number): string | null { return (this.scansMap()[siteId]?.items || [])[0]?.overall_status ?? null; }

  siteBadgeClass(siteId: number): string {
    if (this.hasActiveScans(siteId)) return 'bg-blue-500/20 text-blue-300 border-blue-600';
    switch (this.lastScanStatus(siteId)) {
      case 'OK': return 'bg-green-500/20 text-green-300 border-green-600';
      case 'WARNING': return 'bg-yellow-500/20 text-yellow-300 border-yellow-600';
      case 'CRITICAL': return 'bg-red-500/20 text-red-300 border-red-600';
      default: return 'bg-gray-700 text-gray-400 border-gray-600';
    }
  }

  siteBadgeLabel(siteId: number): string {
    if (this.hasActiveScans(siteId)) return 'En cours...';
    return this.lastScanStatus(siteId) ?? 'Aucun scan';
  }

  siteBadgeIcon(siteId: number): string {
    if (this.hasActiveScans(siteId)) return 'sync';
    switch (this.lastScanStatus(siteId)) {
      case 'OK': return 'verified_user';
      case 'WARNING': return 'warning';
      case 'CRITICAL': return 'gpp_bad';
      default: return 'help_outline';
    }
  }

  statusColor(s: string | null): string {
    switch (s) {
      case 'OK': return 'text-green-400';
      case 'WARNING': return 'text-yellow-400';
      case 'CRITICAL': case 'error': return 'text-red-400';
      case 'done': return 'text-green-400';
      case 'pending': case 'running': return 'text-blue-400';
      default: return 'text-gray-400';
    }
  }

  statusIcon(s: string | null): string {
    switch (s) {
      case 'OK': return 'verified_user';
      case 'WARNING': return 'warning';
      case 'CRITICAL': return 'gpp_bad';
      case 'done': return 'check_circle';
      case 'pending': return 'schedule';
      case 'running': return 'sync';
      case 'error': return 'cancel';
      default: return 'help_outline';
    }
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  get maxSites(): number { return this.subscription()?.plan?.max_sites ?? 0; }
  get canAddSite(): boolean { return this.sites().length < this.maxSites; }

  // --- Score & trend ---
  getScanScore(scan: Scan): number | null { return computeScore(scan.results_json ?? null); }

  getLastScore(siteId: number): number | null {
    const done = (this.scansMap()[siteId]?.items ?? []).find(s => s.status === 'done' && s.results_json);
    return done ? computeScore(done.results_json ?? null) : null;
  }

  getPrevScore(siteId: number): number | null {
    const done = (this.scansMap()[siteId]?.items ?? []).filter(s => s.status === 'done' && s.results_json);
    return done.length >= 2 ? computeScore(done[1].results_json ?? null) : null;
  }

  getTrend(siteId: number): number | null {
    const last = this.getLastScore(siteId);
    const prev = this.getPrevScore(siteId);
    if (last === null || prev === null) return null;
    return last - prev;
  }

  getGrade(score: number): string { return getGrade(score); }
  getScoreColor(score: number): string { return getScoreColor(score); }

  get totalScans(): number {
    return Object.values(this.scansMap()).reduce((sum, p) => sum + (p?.total ?? 0), 0);
  }

  get averageScore(): number | null {
    const scores = this.sites()
      .map(s => this.getLastScore(s.id))
      .filter((s): s is number => s !== null);
    if (scores.length === 0) return null;
    return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  }
}
