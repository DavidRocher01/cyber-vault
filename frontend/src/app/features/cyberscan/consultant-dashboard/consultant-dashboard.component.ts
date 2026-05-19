import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Title } from '@angular/platform-browser';

import { RssiService, RssiClient } from '../services/rssi.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-consultant-dashboard',
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatButtonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule,
    MatSnackBarModule, MatDialogModule, MatFormFieldModule, MatInputModule,
    MatTooltipModule, NavButtonsComponent,
  ],
  templateUrl: './consultant-dashboard.component.html',
})
export class ConsultantDashboardComponent implements OnInit {
  private rssi = inject(RssiService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  clients = signal<RssiClient[]>([]);
  loading = signal(true);
  showAddForm = signal(false);
  saving = signal(false);
  editingId = signal<number | null>(null);
  deletingId = signal<number | null>(null);

  addForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    email: [''],
    description: [''],
  });

  editForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    email: [''],
    description: [''],
  });

  ngOnInit() {
    this.title.setTitle('RSSI Externalisé — CyberScan');
    this.rssi.getClients().subscribe({
      next: c => { this.clients.set(c); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  addClient() {
    if (this.addForm.invalid) return;
    this.saving.set(true);
    const { name, email, description } = this.addForm.getRawValue();
    this.rssi.createClient({ name, email: email || undefined, description: description || undefined }).subscribe({
      next: c => {
        this.clients.update(list => [c, ...list]);
        this.addForm.reset();
        this.showAddForm.set(false);
        this.saving.set(false);
        this.snack.open(`Client "${c.name}" ajouté`, 'OK', { duration: 3000 });
      },
      error: err => {
        this.saving.set(false);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }

  startEdit(client: RssiClient) {
    this.editingId.set(client.id);
    this.editForm.patchValue({ name: client.name, email: client.email ?? '', description: client.description ?? '' });
  }

  cancelEdit() {
    this.editingId.set(null);
    this.editForm.reset();
  }

  saveEdit(clientId: number) {
    if (this.editForm.invalid) return;
    const { name, email, description } = this.editForm.getRawValue();
    this.rssi.updateClient(clientId, { name, email: email || undefined, description: description || undefined }).subscribe({
      next: updated => {
        this.clients.update(list => list.map(c => c.id === clientId ? { ...c, ...updated } : c));
        this.editingId.set(null);
        this.snack.open('Client mis à jour', 'OK', { duration: 3000 });
      },
      error: err => this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 }),
    });
  }

  deleteClient(client: RssiClient) {
    this.deletingId.set(client.id);
    this.rssi.deleteClient(client.id).subscribe({
      next: () => {
        this.clients.update(list => list.filter(c => c.id !== client.id));
        this.deletingId.set(null);
        this.snack.open(`Client "${client.name}" supprimé`, 'OK', { duration: 3000 });
      },
      error: err => {
        this.deletingId.set(null);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }

  statusColor(status: string | null): string {
    switch (status) {
      case 'OK': return 'text-green-400';
      case 'WARNING': return 'text-yellow-400';
      case 'CRITICAL': return 'text-red-400';
      default: return 'text-gray-400';
    }
  }

  statusBgClass(status: string | null): string {
    switch (status) {
      case 'OK': return 'bg-green-500/15 border-green-600/40';
      case 'WARNING': return 'bg-yellow-500/15 border-yellow-600/40';
      case 'CRITICAL': return 'bg-red-500/15 border-red-600/40';
      default: return 'bg-gray-700/30 border-gray-600/40';
    }
  }

  statusIcon(status: string | null): string {
    switch (status) {
      case 'OK': return 'verified_user';
      case 'WARNING': return 'warning';
      case 'CRITICAL': return 'gpp_bad';
      default: return 'help_outline';
    }
  }

  statusLabel(status: string | null): string {
    return status ?? 'Aucun scan';
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  get criticalCount(): number { return this.clients().filter(c => c.worst_status === 'CRITICAL').length; }
  get warningCount(): number { return this.clients().filter(c => c.worst_status === 'WARNING').length; }
  get okCount(): number { return this.clients().filter(c => c.worst_status === 'OK').length; }
}
