import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';

import { DarkwebDossierService, DossierListItem } from '../services/darkweb-dossier.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-darkweb-dossier',
  imports: [
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    NavButtonsComponent,
  ],
  templateUrl: './darkweb-dossier.component.html',
})
export class DarkwebDossierComponent implements OnInit {
  private service = inject(DarkwebDossierService);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  dossiers = signal<DossierListItem[]>([]);
  loading = signal(true);
  deletingId = signal<number | null>(null);

  ngOnInit() {
    this.title.setTitle('Dark Web Dossier — Rocher Cybersécurité');
    this.load();
  }

  private load() {
    this.loading.set(true);
    this.service.list().subscribe({
      next: d => {
        this.dossiers.set(d);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  delete(id: number) {
    this.deletingId.set(id);
    this.service.delete(id).subscribe({
      next: () => {
        this.dossiers.update(list => list.filter(d => d.id !== id));
        this.deletingId.set(null);
        this.snack.open('Dossier supprimé', 'OK', { duration: 3000 });
      },
      error: () => {
        this.deletingId.set(null);
        this.snack.open('Erreur lors de la suppression', 'Fermer', { duration: 3000 });
      },
    });
  }

  riskColor(score: number | null): string {
    if (score === null) return 'text-gray-500';
    if (score >= 50) return 'text-red-400';
    if (score >= 20) return 'text-yellow-400';
    return 'text-green-400';
  }

  riskBg(score: number | null): string {
    if (score === null) return 'bg-gray-800/40 border-gray-700';
    if (score >= 50) return 'bg-red-900/20 border-red-700/40';
    if (score >= 20) return 'bg-yellow-900/20 border-yellow-700/40';
    return 'bg-green-900/20 border-green-700/40';
  }

  riskLabel(score: number | null): string {
    if (score === null) return '—';
    if (score >= 50) return 'Risque élevé';
    if (score >= 20) return 'Risque modéré';
    return 'Risque faible';
  }

  statusLabel(status: string): string {
    switch (status) {
      case 'pending':
        return 'En attente';
      case 'processing':
        return 'Analyse en cours';
      case 'completed':
        return 'Terminé';
      case 'failed':
        return 'Erreur';
      default:
        return status;
    }
  }

  statusColor(status: string): string {
    switch (status) {
      case 'completed':
        return 'text-green-400 bg-green-900/20 border-green-700/40';
      case 'processing':
        return 'text-cyan-400 bg-cyan-900/20 border-cyan-700/40';
      case 'failed':
        return 'text-red-400 bg-red-900/20 border-red-700/40';
      default:
        return 'text-gray-400 bg-gray-800/40 border-gray-700';
    }
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }
}
