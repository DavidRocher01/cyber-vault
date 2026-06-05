import { Component, inject, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatExpansionModule } from '@angular/material/expansion';
import { Title } from '@angular/platform-browser';

import { DarkwebService, DarkwebStatus, DarkwebBreach } from '../services/darkweb.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-darkweb',
  imports: [
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatExpansionModule,
    NavButtonsComponent,
  ],
  templateUrl: './darkweb.component.html',
})
export class DarkwebComponent implements OnInit {
  private service = inject(DarkwebService);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  status = signal<DarkwebStatus | null>(null);
  loading = signal(true);
  checking = signal(false);

  ngOnInit() {
    this.title.setTitle('Dark Web — CyberScan');
    this.service.getStatus().subscribe({
      next: s => {
        this.status.set(s);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  runCheck() {
    this.checking.set(true);
    this.service.runCheck().subscribe({
      next: s => {
        this.status.set(s);
        this.checking.set(false);
        if (s.status === 'OK') {
          this.snack.open('Aucune fuite détectée', 'OK', { duration: 3000 });
        } else if (s.status === 'unknown') {
          this.snack.open(s.error || 'Vérification indisponible', 'Fermer', { duration: 4000 });
        }
      },
      error: () => {
        this.checking.set(false);
        this.snack.open('Erreur lors de la vérification', 'Fermer', { duration: 4000 });
      },
    });
  }

  statusColor(status: string): string {
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

  statusBg(status: string): string {
    switch (status) {
      case 'OK':
        return 'bg-green-900/20 border-green-600/40';
      case 'WARNING':
        return 'bg-yellow-900/20 border-yellow-600/40';
      case 'CRITICAL':
        return 'bg-red-900/20 border-red-600/40';
      default:
        return 'bg-gray-800 border-gray-700';
    }
  }

  statusIcon(status: string): string {
    switch (status) {
      case 'OK':
        return 'verified';
      case 'WARNING':
        return 'warning';
      case 'CRITICAL':
        return 'gpp_bad';
      default:
        return 'help_outline';
    }
  }

  statusLabel(status: string): string {
    switch (status) {
      case 'OK':
        return 'Aucune fuite détectée';
      case 'WARNING':
        return 'Fuite(s) détectée(s)';
      case 'CRITICAL':
        return 'Fuites multiples — Action requise';
      case 'not_checked':
        return 'Non vérifié';
      default:
        return 'Indisponible';
    }
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  formatPwnCount(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
    return n.toString();
  }
}
