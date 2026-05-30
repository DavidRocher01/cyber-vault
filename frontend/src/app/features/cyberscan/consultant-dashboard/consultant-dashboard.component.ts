import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Title } from '@angular/platform-browser';

import {
  RssiService,
  RssiClient,
  DashboardOverview,
  ClientSummary,
  DashboardAlert,
  CalendarEvent,
  DashboardSuggestion,
} from '../services/rssi.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-consultant-dashboard',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    NavButtonsComponent,
  ],
  templateUrl: './consultant-dashboard.component.html',
})
export class ConsultantDashboardComponent implements OnInit {
  private rssi = inject(RssiService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private title = inject(Title);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  // Client list (Sprint 1)
  clients = signal<RssiClient[]>([]);
  loading = signal(true);
  showAddForm = signal(false);
  saving = signal(false);
  editingId = signal<number | null>(null);
  deletingId = signal<number | null>(null);

  // Dashboard data (Sprint 2)
  overview = signal<DashboardOverview | null>(null);
  summaries = signal<ClientSummary[]>([]);
  alerts = signal<DashboardAlert[]>([]);
  events = signal<CalendarEvent[]>([]);
  suggestions = signal<DashboardSuggestion[]>([]);

  // Impersonation (Sprint 3): active client from ?client=X query param
  focusedClientId = signal<number | null>(null);
  focusedClientName = signal<string | null>(null);

  activeTab = signal<'dashboard' | 'clients' | 'awareness'>('dashboard');

  readonly formulas = [
    { value: 'essentiel', label: 'Essentiel' },
    { value: 'premium', label: 'Premium' },
    { value: 'excellence', label: 'Excellence' },
  ];

  addForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    email: [''],
    description: [''],
    formula: [''],
    monthly_amount: [null as number | null],
    contract_renewal_at: [''],
  });

  editForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    email: [''],
    description: [''],
    formula: [''],
    monthly_amount: [null as number | null],
    contract_renewal_at: [''],
    status: [''],
  });

  ngOnInit() {
    this.title.setTitle('RSSI Externalisé — CyberScan');
    this._loadAll();

    const clientParam = this.route.snapshot.queryParamMap.get('client');
    if (clientParam) {
      const id = parseInt(clientParam, 10);
      if (!isNaN(id)) {
        this.focusedClientId.set(id);
        this.rssi.logActivity(id, { action_type: 'view_client' }).subscribe();
      }
    }
  }

  private _loadAll() {
    this.loading.set(true);
    forkJoin({
      clients: this.rssi.getClients(),
      overview: this.rssi.getDashboardOverview(),
      summaries: this.rssi.getClientsSummary(),
      alerts: this.rssi.getDashboardAlerts(),
      events: this.rssi.getUpcomingEvents(14),
      suggestions: this.rssi.getSuggestions(),
    }).subscribe({
      next: data => {
        this.clients.set(data.clients);
        this.overview.set(data.overview);
        this.summaries.set(data.summaries);
        this.alerts.set(data.alerts);
        this.events.set(data.events);
        this.suggestions.set(data.suggestions);
        this.loading.set(false);

        const focusId = this.focusedClientId();
        if (focusId) {
          const found = data.clients.find(c => c.id === focusId);
          this.focusedClientName.set(found?.name ?? null);
        }
      },
      error: () => this.loading.set(false),
    });
  }

  addClient() {
    if (this.addForm.invalid) return;
    this.saving.set(true);
    const v = this.addForm.getRawValue();
    this.rssi
      .createClient({
        name: v.name,
        email: v.email || undefined,
        description: v.description || undefined,
        formula: (v.formula as any) || undefined,
        monthly_amount: v.monthly_amount ?? undefined,
        contract_renewal_at: v.contract_renewal_at || undefined,
      })
      .subscribe({
        next: c => {
          this.addForm.reset();
          this.showAddForm.set(false);
          this.saving.set(false);
          this.snack.open(`Client "${c.name}" ajouté`, 'OK', { duration: 3000 });
          this._loadAll();
        },
        error: err => {
          this.saving.set(false);
          this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
        },
      });
  }

  startEdit(client: RssiClient) {
    this.editingId.set(client.id);
    this.editForm.patchValue({
      name: client.name,
      email: client.email ?? '',
      description: client.description ?? '',
      formula: client.formula ?? '',
      monthly_amount: client.monthly_amount,
      contract_renewal_at: client.contract_renewal_at ?? '',
      status: client.status,
    });
  }

  cancelEdit() {
    this.editingId.set(null);
    this.editForm.reset();
  }

  saveEdit(clientId: number) {
    if (this.editForm.invalid) return;
    const v = this.editForm.getRawValue();
    this.rssi
      .updateClient(clientId, {
        name: v.name,
        email: v.email || undefined,
        description: v.description || undefined,
        formula: (v.formula as any) || undefined,
        monthly_amount: v.monthly_amount ?? undefined,
        contract_renewal_at: v.contract_renewal_at || undefined,
        status: (v.status as any) || undefined,
      })
      .subscribe({
        next: () => {
          this.editingId.set(null);
          this.snack.open('Client mis à jour', 'OK', { duration: 3000 });
          this._loadAll();
        },
        error: err => this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
      });
  }

  deleteClient(client: RssiClient) {
    this.deletingId.set(client.id);
    this.rssi.deleteClient(client.id).subscribe({
      next: () => {
        this.deletingId.set(null);
        this.snack.open(`Client "${client.name}" supprimé`, 'OK', { duration: 3000 });
        this._loadAll();
      },
      error: err => {
        this.deletingId.set(null);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }

  // ── Activity log ──────────────────────────────────────────────────────────────

  onClientRowClick(client: { id: number }) {
    this.router.navigate(['/cyberscan/consultant/clients', client.id]);
  }

  clearFocus() {
    this.focusedClientId.set(null);
    this.focusedClientName.set(null);
  }

  // ── Formatting helpers ────────────────────────────────────────────────────────

  formulaLabel(formula: string | null): string {
    switch (formula) {
      case 'essentiel':
        return 'Essentiel';
      case 'premium':
        return 'Premium';
      case 'excellence':
        return 'Excellence';
      default:
        return '—';
    }
  }

  formulaClass(formula: string | null): string {
    switch (formula) {
      case 'essentiel':
        return 'text-blue-300 bg-blue-500/10 border-blue-600/30';
      case 'premium':
        return 'text-purple-300 bg-purple-500/10 border-purple-600/30';
      case 'excellence':
        return 'text-amber-300 bg-amber-500/10 border-amber-600/30';
      default:
        return 'text-gray-400 bg-gray-700/20 border-gray-600/30';
    }
  }

  clientStatusClass(status: string): string {
    switch (status) {
      case 'active':
        return 'text-green-300';
      case 'inactive':
        return 'text-yellow-300';
      case 'churned':
        return 'text-red-300';
      default:
        return 'text-gray-400';
    }
  }

  statusColor(status: string | null): string {
    switch (status) {
      case 'OK':
        return 'text-green-400';
      case 'WARNING':
        return 'text-yellow-400';
      case 'CRITICAL':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  }

  statusBgClass(status: string | null): string {
    switch (status) {
      case 'OK':
        return 'bg-green-500/15 border-green-600/40';
      case 'WARNING':
        return 'bg-yellow-500/15 border-yellow-600/40';
      case 'CRITICAL':
        return 'bg-red-500/15 border-red-600/40';
      default:
        return 'bg-gray-700/30 border-gray-600/40';
    }
  }

  statusIcon(status: string | null): string {
    switch (status) {
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

  statusLabel(status: string | null): string {
    return status ?? 'Aucun scan';
  }

  alertSeverityClass(severity: string): string {
    switch (severity) {
      case 'critical':
        return 'border-red-600/50 bg-red-500/10';
      case 'high':
        return 'border-orange-600/50 bg-orange-500/10';
      default:
        return 'border-yellow-600/50 bg-yellow-500/10';
    }
  }

  alertIconColor(severity: string): string {
    switch (severity) {
      case 'critical':
        return 'text-red-400';
      case 'high':
        return 'text-orange-400';
      default:
        return 'text-yellow-400';
    }
  }

  suggestionIcon(type: string): string {
    switch (type) {
      case 'upsell_opportunity':
        return 'trending_up';
      case 'engagement_alert':
        return 'notification_important';
      case 'renewal_upcoming':
        return 'event_available';
      case 'high_overdue':
        return 'assignment_late';
      default:
        return 'lightbulb';
    }
  }

  visitTypeLabel(type: string): string {
    switch (type) {
      case 'monthly':
        return 'Mensuelle';
      case 'quarterly':
        return 'Trimestrielle';
      case 'annual':
        return 'Annuelle';
      case 'urgent':
        return 'Urgente';
      default:
        return type;
    }
  }

  locationLabel(loc: string): string {
    return loc === 'onsite' ? 'Sur site' : 'À distance';
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  formatAmount(amount: number | null): string {
    if (amount == null) return '—';
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(amount);
  }

  get totalMrr(): number {
    return this.clients()
      .filter(c => c.status === 'active' && c.monthly_amount != null)
      .reduce((sum, c) => sum + (c.monthly_amount ?? 0), 0);
  }

  get criticalCount(): number {
    return this.clients().filter(c => c.worst_status === 'CRITICAL').length;
  }
  get warningCount(): number {
    return this.clients().filter(c => c.worst_status === 'WARNING').length;
  }
  get okCount(): number {
    return this.clients().filter(c => c.worst_status === 'OK').length;
  }
}
