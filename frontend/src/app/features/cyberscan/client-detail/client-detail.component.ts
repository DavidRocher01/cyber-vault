import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin, Observable, of, switchMap } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Title } from '@angular/platform-browser';

import {
  RssiService,
  RssiClient,
  RssiVisit,
  RssiAction,
  ActivityLogEntry,
  RssiDeliverable,
  RssiSite,
  UnlinkedSite,
} from '../services/rssi.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-client-detail',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    NavButtonsComponent,
  ],
  templateUrl: './client-detail.component.html',
})
export class ClientDetailComponent implements OnInit {
  private rssi = inject(RssiService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private title = inject(Title);

  clientId = 0;

  loading = signal(true);
  client = signal<RssiClient | null>(null);
  visits = signal<RssiVisit[]>([]);
  actions = signal<RssiAction[]>([]);
  activityLog = signal<ActivityLogEntry[]>([]);
  deliverables = signal<RssiDeliverable[]>([]);
  sites = signal<RssiSite[]>([]);
  unlinkedSites = signal<UnlinkedSite[]>([]);
  showLinkSitePicker = signal(false);
  selectedSiteId = signal<number | null>(null);

  activeTab = signal<'infos' | 'visites' | 'actions' | 'livrables' | 'sites' | 'activite'>('infos');
  saving = signal(false);
  generatingReport = signal(false);
  editingVisitId = signal<number | null>(null);
  editingActionId = signal<number | null>(null);
  editingDeliverableId = signal<number | null>(null);
  showAddVisit = signal(false);
  showAddAction = signal(false);
  showAddDeliverable = signal(false);

  confirmDelete = signal<{ type: 'visit' | 'action' | 'deliverable' | 'site'; id: number } | null>(
    null
  );

  actionsStatusFilter = signal<string>('all');
  actionsPriorityFilter = signal<string>('all');

  filteredActions = computed(() => {
    let list = this.actions();
    const s = this.actionsStatusFilter();
    const p = this.actionsPriorityFilter();
    if (s !== 'all') list = list.filter(a => a.status === s);
    if (p !== 'all') list = list.filter(a => a.priority === p);
    return list;
  });

  readonly formulas = [
    { value: 'essentiel', label: 'Essentiel' },
    { value: 'premium', label: 'Premium' },
    { value: 'excellence', label: 'Excellence' },
  ];

  readonly visitTypes = [
    { value: 'monthly', label: 'Mensuelle' },
    { value: 'quarterly', label: 'Trimestrielle' },
    { value: 'annual', label: 'Annuelle' },
    { value: 'urgent', label: 'Urgente' },
  ];

  readonly visitStatuses = [
    { value: 'planned', label: 'Planifiée' },
    { value: 'completed', label: 'Complétée' },
    { value: 'cancelled', label: 'Annulée' },
    { value: 'postponed', label: 'Reportée' },
  ];

  readonly actionPriorities = [
    { value: 'critical', label: 'Critique' },
    { value: 'high', label: 'Haute' },
    { value: 'medium', label: 'Moyenne' },
    { value: 'low', label: 'Basse' },
  ];

  readonly actionStatuses = [
    { value: 'open', label: 'Ouverte' },
    { value: 'in_progress', label: 'En cours' },
    { value: 'done', label: 'Terminée' },
    { value: 'cancelled', label: 'Annulée' },
    { value: 'postponed', label: 'Reportée' },
  ];

  readonly docTypes = [
    { value: 'compte_rendu', label: 'Compte-rendu' },
    { value: 'rapport', label: 'Rapport' },
    { value: 'recommandation', label: 'Recommandation' },
    { value: 'contrat', label: 'Contrat' },
    { value: 'autre', label: 'Autre' },
  ];

  infoForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    email: [''],
    description: [''],
    formula: [''],
    monthly_amount: [null as number | null],
    contract_renewal_at: [''],
    status: [''],
    notion_workspace_url: [''],
    pipedrive_deal_id: [''],
    pennylane_customer_id: [''],
  });

  addVisitForm = this.fb.nonNullable.group({
    scheduled_date: ['', Validators.required],
    visit_type: ['monthly'],
    location: ['onsite'],
    notes: [''],
  });

  editVisitForm = this.fb.nonNullable.group({
    scheduled_date: ['', Validators.required],
    visit_type: ['monthly'],
    location: ['onsite'],
    status: ['planned'],
    notes: [''],
    actual_date: [''],
    duration_hours: [null as number | null],
  });

  addActionForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    description: [''],
    category: [''],
    priority: ['medium'],
    assigned_to: [''],
    due_date: [''],
  });

  editActionForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    description: [''],
    category: [''],
    priority: ['medium'],
    status: ['open'],
    assigned_to: [''],
    due_date: [''],
  });

  addDeliverableForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    doc_type: ['compte_rendu'],
    delivered_at: ['', Validators.required],
    file_url: [''],
    notes: [''],
  });

  editDeliverableForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    doc_type: ['compte_rendu'],
    delivered_at: ['', Validators.required],
    file_url: [''],
    notes: [''],
  });

  pendingAddFile = signal<File | null>(null);
  pendingEditFile = signal<File | null>(null);
  uploadingFile = signal(false);

  ngOnInit() {
    this.clientId = Number(this.route.snapshot.paramMap.get('id'));
    this._loadAll();
    this.rssi.logActivity(this.clientId, { action_type: 'view_client' }).subscribe();
  }

  private _loadAll() {
    this.loading.set(true);
    forkJoin({
      client: this.rssi.getClient(this.clientId),
      visits: this.rssi.getVisits(this.clientId),
      actions: this.rssi.getActions(this.clientId),
      activity: this.rssi.getActivityLog(this.clientId),
      deliverables: this.rssi.getDeliverables(this.clientId),
      sites: this.rssi.getClientSites(this.clientId),
      unlinked: this.rssi.getUnlinkedSites(),
    }).subscribe({
      next: data => {
        this.client.set(data.client);
        this.visits.set(data.visits);
        this.actions.set(data.actions);
        this.activityLog.set(data.activity);
        this.deliverables.set(data.deliverables);
        this.sites.set(data.sites);
        this.unlinkedSites.set(data.unlinked);
        this.title.setTitle(`${data.client.name} — RSSI CyberScan`);
        this._patchInfoForm(data.client);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.router.navigate(['/cyberscan/consultant']);
      },
    });
  }

  private _patchInfoForm(c: RssiClient) {
    this.infoForm.patchValue({
      name: c.name,
      email: c.email ?? '',
      description: c.description ?? '',
      formula: c.formula ?? '',
      monthly_amount: c.monthly_amount,
      contract_renewal_at: c.contract_renewal_at ?? '',
      status: c.status,
      notion_workspace_url: c.notion_workspace_url ?? '',
      pipedrive_deal_id: c.pipedrive_deal_id ?? '',
      pennylane_customer_id: c.pennylane_customer_id ?? '',
    });
  }

  // ── CSV export ────────────────────────────────────────────────────────────

  exportingCsv = signal(false);

  exportActionsCsv() {
    this.exportingCsv.set(true);
    this.rssi.exportActionsCsv(this.clientId).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `actions_${this.clientId}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        this.exportingCsv.set(false);
      },
      error: () => {
        this.exportingCsv.set(false);
        this.snack.open("Erreur lors de l'export CSV", 'Fermer', { duration: 4000 });
      },
    });
  }

  // ── PDF report ────────────────────────────────────────────────────────────

  downloadReport() {
    this.generatingReport.set(true);
    this.rssi.downloadReport(this.clientId).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const name = (this.client()?.name ?? 'client').replace(/\s+/g, '_').toLowerCase();
        a.href = url;
        a.download = `rapport_rssi_${name}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        this.generatingReport.set(false);
        this.rssi.logActivity(this.clientId, { action_type: 'generate_report' }).subscribe();
      },
      error: () => {
        this.generatingReport.set(false);
        this.snack.open('Erreur lors de la génération du rapport', 'Fermer', { duration: 4000 });
      },
    });
  }

  // ── Infos ─────────────────────────────────────────────────────────────────

  saveInfo() {
    if (this.infoForm.invalid) return;
    this.saving.set(true);
    const v = this.infoForm.getRawValue();
    this.rssi
      .updateClient(this.clientId, {
        name: v.name,
        email: v.email || undefined,
        description: v.description || undefined,
        formula: (v.formula as any) || undefined,
        monthly_amount: v.monthly_amount ?? undefined,
        contract_renewal_at: v.contract_renewal_at || undefined,
        status: (v.status as any) || undefined,
        notion_workspace_url: v.notion_workspace_url || undefined,
        pipedrive_deal_id: v.pipedrive_deal_id || undefined,
        pennylane_customer_id: v.pennylane_customer_id || undefined,
      })
      .subscribe({
        next: updated => {
          this.client.set(updated);
          this.saving.set(false);
          this.snack.open('Client mis à jour', 'OK', { duration: 3000 });
        },
        error: err => {
          this.saving.set(false);
          this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
        },
      });
  }

  // ── Visits ────────────────────────────────────────────────────────────────

  addVisit() {
    if (this.addVisitForm.invalid) return;
    this.saving.set(true);
    const v = this.addVisitForm.getRawValue();
    this.rssi
      .createVisit(this.clientId, {
        scheduled_date: v.scheduled_date,
        visit_type: v.visit_type as any,
        location: v.location as any,
        notes: v.notes || undefined,
      })
      .subscribe({
        next: visit => {
          this.visits.update(list => [visit, ...list]);
          this.addVisitForm.reset({ visit_type: 'monthly', location: 'onsite' });
          this.showAddVisit.set(false);
          this.saving.set(false);
          this.snack.open('Visite planifiée', 'OK', { duration: 3000 });
          this.rssi
            .logActivity(this.clientId, { action_type: 'create_visit', resource_id: visit.id })
            .subscribe();
        },
        error: err => {
          this.saving.set(false);
          this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
        },
      });
  }

  startEditVisit(v: RssiVisit) {
    this.editingVisitId.set(v.id);
    this.editVisitForm.patchValue({
      scheduled_date: v.scheduled_date,
      visit_type: v.visit_type,
      location: v.location,
      status: v.status,
      notes: v.notes ?? '',
      actual_date: v.actual_date ?? '',
      duration_hours: v.duration_hours,
    });
  }

  saveVisit(visitId: number) {
    if (this.editVisitForm.invalid) return;
    const v = this.editVisitForm.getRawValue();
    this.rssi
      .updateVisit(this.clientId, visitId, {
        scheduled_date: v.scheduled_date,
        visit_type: v.visit_type as any,
        location: v.location as any,
        status: v.status as any,
        notes: v.notes || undefined,
        actual_date: v.actual_date || undefined,
        duration_hours: v.duration_hours ?? undefined,
      })
      .subscribe({
        next: updated => {
          this.visits.update(list => list.map(x => (x.id === visitId ? updated : x)));
          this.editingVisitId.set(null);
          this.snack.open('Visite mise à jour', 'OK', { duration: 3000 });
          this.rssi
            .logActivity(this.clientId, { action_type: 'update_visit', resource_id: visitId })
            .subscribe();
        },
        error: err => this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
      });
  }

  deleteVisit(visitId: number) {
    this.confirmDelete.set({ type: 'visit', id: visitId });
  }

  private _doDeleteVisit(visitId: number) {
    this.rssi.deleteVisit(this.clientId, visitId).subscribe({
      next: () => {
        this.visits.update(list => list.filter(v => v.id !== visitId));
        this.snack.open('Visite supprimée', 'OK', { duration: 3000 });
      },
      error: err => this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
    });
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  addAction() {
    if (this.addActionForm.invalid) return;
    this.saving.set(true);
    const v = this.addActionForm.getRawValue();
    this.rssi
      .createAction(this.clientId, {
        title: v.title,
        description: v.description || undefined,
        category: (v.category as any) || undefined,
        priority: v.priority as any,
        assigned_to: v.assigned_to || undefined,
        due_date: v.due_date || undefined,
      })
      .subscribe({
        next: action => {
          this.actions.update(list => [action, ...list]);
          this.addActionForm.reset({ priority: 'medium' });
          this.showAddAction.set(false);
          this.saving.set(false);
          this.snack.open('Action créée', 'OK', { duration: 3000 });
          this.rssi
            .logActivity(this.clientId, { action_type: 'create_action', resource_id: action.id })
            .subscribe();
        },
        error: err => {
          this.saving.set(false);
          this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
        },
      });
  }

  startEditAction(a: RssiAction) {
    this.editingActionId.set(a.id);
    this.editActionForm.patchValue({
      title: a.title,
      description: a.description ?? '',
      category: a.category ?? '',
      priority: a.priority,
      status: a.status,
      assigned_to: a.assigned_to ?? '',
      due_date: a.due_date ?? '',
    });
  }

  saveAction(actionId: number) {
    if (this.editActionForm.invalid) return;
    const v = this.editActionForm.getRawValue();
    this.rssi
      .updateAction(this.clientId, actionId, {
        title: v.title,
        description: v.description || undefined,
        category: (v.category as any) || undefined,
        priority: v.priority as any,
        status: v.status as any,
        assigned_to: v.assigned_to || undefined,
        due_date: v.due_date || undefined,
      })
      .subscribe({
        next: updated => {
          this.actions.update(list => list.map(x => (x.id === actionId ? updated : x)));
          this.editingActionId.set(null);
          this.snack.open('Action mise à jour', 'OK', { duration: 3000 });
          this.rssi
            .logActivity(this.clientId, { action_type: 'update_action', resource_id: actionId })
            .subscribe();
        },
        error: err => this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
      });
  }

  deleteAction(actionId: number) {
    this.confirmDelete.set({ type: 'action', id: actionId });
  }

  private _doDeleteAction(actionId: number) {
    this.rssi.deleteAction(this.clientId, actionId).subscribe({
      next: () => {
        this.actions.update(list => list.filter(a => a.id !== actionId));
        this.snack.open('Action supprimée', 'OK', { duration: 3000 });
      },
      error: err => this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
    });
  }

  // ── Deliverables ──────────────────────────────────────────────────────────

  onAddFileChange(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0] ?? null;
    this.pendingAddFile.set(file);
    if (file) this.addDeliverableForm.patchValue({ file_url: file.name });
  }

  onEditFileChange(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0] ?? null;
    this.pendingEditFile.set(file);
    if (file) this.editDeliverableForm.patchValue({ file_url: file.name });
  }

  addDeliverable() {
    if (this.addDeliverableForm.invalid) return;
    this.saving.set(true);
    const v = this.addDeliverableForm.getRawValue();
    const file = this.pendingAddFile();

    const upload$: Observable<{ key: string; filename: string } | null> = file
      ? this.rssi.uploadDeliverableFile(this.clientId, file)
      : of(null);

    upload$
      .pipe(
        switchMap((uploaded: { key: string; filename: string } | null) =>
          this.rssi.createDeliverable(this.clientId, {
            title: v.title,
            doc_type: v.doc_type as any,
            delivered_at: v.delivered_at,
            file_url: uploaded?.key ?? (v.file_url || undefined),
            notes: v.notes || undefined,
          })
        )
      )
      .subscribe({
        next: (d: RssiDeliverable) => {
          this.deliverables.update(list => [d, ...list]);
          this.addDeliverableForm.reset({ doc_type: 'compte_rendu' });
          this.pendingAddFile.set(null);
          this.showAddDeliverable.set(false);
          this.saving.set(false);
          this.snack.open('Livrable ajouté', 'OK', { duration: 3000 });
          this.rssi
            .logActivity(this.clientId, { action_type: 'send_deliverable', resource_id: d.id })
            .subscribe();
        },
        error: (err: { error?: { detail?: string } }) => {
          this.saving.set(false);
          this.snack.open(err.error?.detail || "Erreur lors de l'upload", 'Fermer', {
            duration: 4000,
          });
        },
      });
  }

  startEditDeliverable(d: RssiDeliverable) {
    this.editingDeliverableId.set(d.id);
    this.pendingEditFile.set(null);
    this.editDeliverableForm.patchValue({
      title: d.title,
      doc_type: d.doc_type,
      delivered_at: d.delivered_at,
      file_url: d.file_url ?? '',
      notes: d.notes ?? '',
    });
  }

  saveDeliverable(deliverableId: number) {
    if (this.editDeliverableForm.invalid) return;
    const v = this.editDeliverableForm.getRawValue();
    const file = this.pendingEditFile();

    const upload$: Observable<{ key: string; filename: string } | null> = file
      ? this.rssi.uploadDeliverableFile(this.clientId, file)
      : of(null);

    upload$
      .pipe(
        switchMap((uploaded: { key: string; filename: string } | null) =>
          this.rssi.updateDeliverable(this.clientId, deliverableId, {
            title: v.title,
            doc_type: v.doc_type as any,
            delivered_at: v.delivered_at,
            file_url: uploaded?.key ?? (v.file_url || undefined),
            notes: v.notes || undefined,
          })
        )
      )
      .subscribe({
        next: (updated: RssiDeliverable) => {
          this.deliverables.update(list => list.map(x => (x.id === deliverableId ? updated : x)));
          this.editingDeliverableId.set(null);
          this.pendingEditFile.set(null);
          this.snack.open('Livrable mis à jour', 'OK', { duration: 3000 });
        },
        error: (err: { error?: { detail?: string } }) =>
          this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
      });
  }

  openDeliverableFile(deliverable: RssiDeliverable) {
    if (!deliverable.file_url) return;
    this.rssi.getDeliverableDownloadUrl(this.clientId, deliverable.id).subscribe({
      next: ({ url }) => window.open(url, '_blank', 'noopener'),
      error: () => this.snack.open("Impossible d'ouvrir le fichier", 'Fermer', { duration: 4000 }),
    });
  }

  deleteDeliverable(deliverableId: number) {
    this.confirmDelete.set({ type: 'deliverable', id: deliverableId });
  }

  private _doDeleteDeliverable(deliverableId: number) {
    this.rssi.deleteDeliverable(this.clientId, deliverableId).subscribe({
      next: () => {
        this.deliverables.update(list => list.filter(d => d.id !== deliverableId));
        this.snack.open('Livrable supprimé', 'OK', { duration: 3000 });
      },
      error: err => this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
    });
  }

  docTypeLabel(t: string): string {
    const map: Record<string, string> = {
      compte_rendu: 'Compte-rendu',
      rapport: 'Rapport',
      recommandation: 'Recommandation',
      contrat: 'Contrat',
      autre: 'Autre',
    };
    return map[t] ?? t;
  }

  docTypeClass(t: string): string {
    switch (t) {
      case 'compte_rendu':
        return 'text-blue-300 bg-blue-500/10 border-blue-600/30';
      case 'rapport':
        return 'text-cyan-300 bg-cyan-500/10 border-cyan-600/30';
      case 'recommandation':
        return 'text-purple-300 bg-purple-500/10 border-purple-600/30';
      case 'contrat':
        return 'text-amber-300 bg-amber-500/10 border-amber-600/30';
      default:
        return 'text-gray-400 bg-gray-700/20 border-gray-600/30';
    }
  }

  // ── Formatting helpers ────────────────────────────────────────────────────

  formulaLabel(f: string | null): string {
    const map: Record<string, string> = {
      essentiel: 'Essentiel',
      premium: 'Premium',
      excellence: 'Excellence',
    };
    return f ? (map[f] ?? f) : '—';
  }

  formulaClass(f: string | null): string {
    switch (f) {
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

  statusClass(status: string): string {
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

  priorityClass(p: string): string {
    switch (p) {
      case 'critical':
        return 'text-red-400 bg-red-500/10 border-red-600/30';
      case 'high':
        return 'text-orange-400 bg-orange-500/10 border-orange-600/30';
      case 'medium':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-600/30';
      default:
        return 'text-gray-400 bg-gray-700/20 border-gray-600/30';
    }
  }

  actionStatusClass(s: string): string {
    switch (s) {
      case 'done':
        return 'text-green-400 bg-green-500/10 border-green-600/30';
      case 'in_progress':
        return 'text-blue-400 bg-blue-500/10 border-blue-600/30';
      case 'cancelled':
        return 'text-gray-500 bg-gray-700/20 border-gray-600/30';
      case 'postponed':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-600/30';
      default:
        return 'text-white bg-gray-700/30 border-gray-600/40';
    }
  }

  visitStatusClass(s: string): string {
    switch (s) {
      case 'completed':
        return 'text-green-400';
      case 'cancelled':
        return 'text-red-400';
      case 'postponed':
        return 'text-yellow-400';
      default:
        return 'text-blue-300';
    }
  }

  actionStatusLabel(s: string): string {
    const map: Record<string, string> = {
      open: 'Ouverte',
      in_progress: 'En cours',
      done: 'Terminée',
      cancelled: 'Annulée',
      postponed: 'Reportée',
    };
    return map[s] ?? s;
  }

  visitStatusLabel(s: string): string {
    const map: Record<string, string> = {
      planned: 'Planifiée',
      completed: 'Complétée',
      cancelled: 'Annulée',
      postponed: 'Reportée',
    };
    return map[s] ?? s;
  }

  visitTypeLabel(t: string): string {
    const map: Record<string, string> = {
      monthly: 'Mensuelle',
      quarterly: 'Trimestrielle',
      annual: 'Annuelle',
      urgent: 'Urgente',
    };
    return map[t] ?? t;
  }

  locationLabel(l: string): string {
    return l === 'onsite' ? 'Sur site' : 'À distance';
  }

  activityLabel(type: string): string {
    const map: Record<string, string> = {
      view_client: 'Consultation fiche client',
      view_sites: 'Consultation des sites',
      view_scans: 'Consultation des scans',
      view_findings: 'Consultation des findings',
      generate_report: 'Génération de rapport',
      send_deliverable: "Envoi d'un livrable",
      create_action: "Création d'une action",
      update_action: "Mise à jour d'une action",
      create_visit: "Planification d'une visite",
      update_visit: "Mise à jour d'une visite",
    };
    return map[type] ?? type;
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  formatDateTime(d: string): string {
    return new Date(d).toLocaleString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
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

  readonly today = new Date().toISOString().slice(0, 10);

  get openActionsCount(): number {
    return this.actions().filter(a => a.status === 'open' || a.status === 'in_progress').length;
  }

  get overdueActionsCount(): number {
    const today = new Date().toISOString().slice(0, 10);
    return this.actions().filter(
      a => (a.status === 'open' || a.status === 'in_progress') && a.due_date && a.due_date < today
    ).length;
  }

  // ── Confirmation suppression ──────────────────────────────────────────────

  confirmDeleteConfirm() {
    const cd = this.confirmDelete();
    if (!cd) return;
    this.confirmDelete.set(null);
    switch (cd.type) {
      case 'visit':
        this._doDeleteVisit(cd.id);
        break;
      case 'action':
        this._doDeleteAction(cd.id);
        break;
      case 'deliverable':
        this._doDeleteDeliverable(cd.id);
        break;
      case 'site':
        this._doUnlinkSite(cd.id);
        break;
    }
  }

  confirmDeleteLabel(): string {
    const cd = this.confirmDelete();
    if (!cd) return '';
    switch (cd.type) {
      case 'visit':
        return 'Supprimer cette visite ?';
      case 'action':
        return 'Supprimer cette action ?';
      case 'deliverable':
        return 'Supprimer ce livrable ?';
      case 'site':
        return 'Délier ce site du client ?';
    }
  }

  // ── Sites link/unlink ─────────────────────────────────────────────────────

  openLinkPicker() {
    this.rssi.getUnlinkedSites().subscribe(list => {
      this.unlinkedSites.set(list);
      this.selectedSiteId.set(null);
      this.showLinkSitePicker.set(true);
    });
  }

  linkSite() {
    const siteId = this.selectedSiteId();
    if (!siteId) return;
    this.rssi.linkSite(this.clientId, siteId).subscribe({
      next: linked => {
        this.sites.update(list => [linked, ...list]);
        this.unlinkedSites.update(list => list.filter(s => s.id !== siteId));
        this.showLinkSitePicker.set(false);
        this.selectedSiteId.set(null);
        this.snack.open('Site lié avec succès', 'OK', { duration: 3000 });
      },
      error: err => this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
    });
  }

  unlinkSite(siteId: number) {
    this.confirmDelete.set({ type: 'site', id: siteId });
  }

  private _doUnlinkSite(siteId: number) {
    this.rssi.unlinkSite(this.clientId, siteId).subscribe({
      next: () => {
        const removed = this.sites().find(s => s.id === siteId);
        this.sites.update(list => list.filter(s => s.id !== siteId));
        if (removed) {
          this.unlinkedSites.update(list => [
            ...list,
            { id: removed.id, url: removed.url, name: removed.name },
          ]);
        }
        this.snack.open('Site délié', 'OK', { duration: 3000 });
      },
      error: err => this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
    });
  }

  scanStatusClass(s: 'OK' | 'WARNING' | 'CRITICAL' | null): string {
    switch (s) {
      case 'OK':
        return 'text-green-400 bg-green-500/10 border-green-600/30';
      case 'WARNING':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-600/30';
      case 'CRITICAL':
        return 'text-red-400 bg-red-500/10 border-red-600/30';
      default:
        return 'text-gray-500 bg-gray-700/20 border-gray-600/30';
    }
  }

  scanStatusLabel(s: 'OK' | 'WARNING' | 'CRITICAL' | null): string {
    if (!s) return 'Aucun scan';
    return s;
  }
}
