import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatChipsModule } from '@angular/material/chips';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subscription, interval } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import { CyberscanService, Site, Scan, Subscription as UserSubscription } from '../services/cyberscan.service';

type ScanFilter = 'all' | 'done' | 'running' | 'error';

@Component({
  selector: 'app-cyberscan-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatFormFieldModule,
    MatInputModule,
    MatChipsModule,
    MatSelectModule,
    MatSnackBarModule,
  ],
  templateUrl: './dashboard.component.html',
})
export class DashboardComponent implements OnInit, OnDestroy {
  private cyberscan = inject(CyberscanService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private route = inject(ActivatedRoute);
  private pollingMap: Record<number, Subscription> = {};

  subscription = signal<UserSubscription | null>(null);
  sites = signal<Site[]>([]);
  scansMap = signal<Record<number, Scan[]>>({});
  loadingScans = signal<Record<number, boolean>>({});
  triggeringScans = signal<Record<number, boolean>>({});
  scanFilter = signal<ScanFilter>('all');

  loading = signal(true);
  addingSite = signal(false);
  showAddForm = signal(false);

  siteForm = this.fb.nonNullable.group({
    url: ['', [Validators.required, Validators.pattern(/^https?:\/\/.+/)]],
    name: ['', Validators.required],
  });

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      if (params['subscribed'] === 'true') {
        this.snack.open('Abonnement activé ! Bienvenue sur CyberScan.', 'Super', { duration: 6000 });
      }
    });
    this.loadDashboard();
  }

  ngOnDestroy() {
    Object.values(this.pollingMap).forEach(sub => sub.unsubscribe());
  }

  loadDashboard() {
    this.loading.set(true);
    this.cyberscan.getMySubscription().subscribe({
      next: sub => this.subscription.set(sub),
      error: () => {},
    });
    this.cyberscan.getMySites().subscribe({
      next: sites => {
        this.sites.set(sites);
        this.loading.set(false);
        sites.forEach(s => this.loadScans(s.id));
      },
      error: () => this.loading.set(false),
    });
  }

  loadScans(siteId: number) {
    this.loadingScans.update(m => ({ ...m, [siteId]: true }));
    this.cyberscan.getSiteScans(siteId).subscribe({
      next: scans => {
        this.scansMap.update(m => ({ ...m, [siteId]: scans }));
        this.loadingScans.update(m => ({ ...m, [siteId]: false }));
        this.maybeStartPolling(siteId, scans);
      },
      error: () => this.loadingScans.update(m => ({ ...m, [siteId]: false })),
    });
  }

  maybeStartPolling(siteId: number, scans: Scan[]) {
    const hasActive = scans.some(s => s.status === 'pending' || s.status === 'running');
    if (!hasActive || this.pollingMap[siteId]) return;

    this.pollingMap[siteId] = interval(4000).pipe(
      switchMap(() => this.cyberscan.getSiteScans(siteId)),
      takeWhile(s => s.some(x => x.status === 'pending' || x.status === 'running'), true),
    ).subscribe(scans => {
      this.scansMap.update(m => ({ ...m, [siteId]: scans }));
      const stillActive = scans.some(s => s.status === 'pending' || s.status === 'running');
      if (!stillActive) delete this.pollingMap[siteId];
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
        this.loadScans(site.id);
      },
      error: err => {
        this.addingSite.set(false);
        this.snack.open(err.error?.detail || "Erreur lors de l'ajout", 'Fermer', { duration: 5000 });
      },
    });
  }

  deleteSite(site: Site) {
    if (!confirm(`Supprimer ${site.name} ?`)) return;
    this.cyberscan.deleteSite(site.id).subscribe({
      next: () => {
        this.sites.update(s => s.filter(x => x.id !== site.id));
        this.snack.open('Site supprimé', 'OK', { duration: 3000 });
      },
    });
  }

  triggerScan(siteId: number) {
    this.triggeringScans.update(m => ({ ...m, [siteId]: true }));
    this.cyberscan.triggerScan(siteId).subscribe({
      next: () => {
        this.triggeringScans.update(m => ({ ...m, [siteId]: false }));
        this.snack.open('Scan lancé — mise à jour automatique en cours', 'OK', { duration: 5000 });
        this.loadScans(siteId);
      },
      error: err => {
        this.triggeringScans.update(m => ({ ...m, [siteId]: false }));
        this.snack.open(err.error?.detail || 'Erreur lors du lancement', 'Fermer', { duration: 5000 });
      },
    });
  }

  openBillingPortal() {
    this.cyberscan.getBillingPortal().subscribe({
      next: res => window.location.href = res.checkout_url,
    });
  }

  downloadPdf(scanId: number) {
    window.open(this.cyberscan.downloadPdf(scanId), '_blank');
  }

  getScans(siteId: number): Scan[] {
    const all = this.scansMap()[siteId] || [];
    const f = this.scanFilter();
    if (f === 'all') return all;
    if (f === 'running') return all.filter(s => s.status === 'pending' || s.status === 'running');
    return all.filter(s => s.status === f);
  }

  isLoadingScans(siteId: number): boolean {
    return this.loadingScans()[siteId] || false;
  }

  isTriggeringScans(siteId: number): boolean {
    return this.triggeringScans()[siteId] || false;
  }

  hasActiveScans(siteId: number): boolean {
    return (this.scansMap()[siteId] || []).some(s => s.status === 'pending' || s.status === 'running');
  }

  lastScanStatus(siteId: number): string | null {
    return (this.scansMap()[siteId] || [])[0]?.overall_status ?? null;
  }

  siteBadgeClass(siteId: number): string {
    const status = this.lastScanStatus(siteId);
    if (this.hasActiveScans(siteId)) return 'bg-blue-500/20 text-blue-300 border-blue-600';
    switch (status) {
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

  statusColor(status: string | null): string {
    switch (status) {
      case 'OK': return 'text-green-400';
      case 'WARNING': return 'text-yellow-400';
      case 'CRITICAL': return 'text-red-400';
      case 'done': return 'text-green-400';
      case 'pending':
      case 'running': return 'text-blue-400';
      case 'error': return 'text-red-400';
      default: return 'text-gray-400';
    }
  }

  statusIcon(status: string | null): string {
    switch (status) {
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

  formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  get maxSites(): number {
    return this.subscription()?.plan?.max_sites ?? 0;
  }

  get canAddSite(): boolean {
    return this.sites().length < this.maxSites;
  }
}
