import { Component, inject, OnInit, signal } from '@angular/core';
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
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { CyberscanService, Site, Scan, Subscription } from '../services/cyberscan.service';

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
    MatExpansionModule,
    MatDialogModule,
    MatSnackBarModule,
  ],
  templateUrl: './dashboard.component.html',
})
export class DashboardComponent implements OnInit {
  private cyberscan = inject(CyberscanService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private route = inject(ActivatedRoute);

  subscription = signal<Subscription | null>(null);
  sites = signal<Site[]>([]);
  scansMap = signal<Record<number, Scan[]>>({});
  loadingScans = signal<Record<number, boolean>>({});
  triggeringScans = signal<Record<number, boolean>>({});

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
      },
      error: () => this.loadingScans.update(m => ({ ...m, [siteId]: false })),
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
        const msg = err.error?.detail || 'Erreur lors de l\'ajout';
        this.snack.open(msg, 'Fermer', { duration: 5000 });
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
      next: res => {
        this.triggeringScans.update(m => ({ ...m, [siteId]: false }));
        this.snack.open('Scan lancé — le rapport sera disponible dans quelques instants', 'OK', { duration: 6000 });
        setTimeout(() => this.loadScans(siteId), 3000);
      },
      error: err => {
        this.triggeringScans.update(m => ({ ...m, [siteId]: false }));
        const msg = err.error?.detail || 'Erreur lors du lancement du scan';
        this.snack.open(msg, 'Fermer', { duration: 5000 });
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
    return this.scansMap()[siteId] || [];
  }

  isLoadingScans(siteId: number): boolean {
    return this.loadingScans()[siteId] || false;
  }

  isTriggeringScans(siteId: number): boolean {
    return this.triggeringScans()[siteId] || false;
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
      case 'OK': return 'check_circle';
      case 'WARNING': return 'warning';
      case 'CRITICAL': return 'error';
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
