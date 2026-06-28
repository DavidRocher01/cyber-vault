import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Title } from '@angular/platform-browser';

import { CollabService, Collaborator } from '../services/collab.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-collab-accept',
  imports: [
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    NavButtonsComponent,
  ],
  template: `
    <app-nav-buttons />
    <div class="min-h-screen bg-gray-950 flex items-center justify-center px-6">
      <div class="max-w-md w-full bg-gray-900 border border-gray-800 rounded-2xl p-8 text-center">
        @if (loading()) {
          <mat-spinner [diameter]="48" class="mx-auto mb-4" />
          <p class="text-gray-400">Vérification de l'invitation…</p>
        } @else if (error()) {
          <mat-icon class="text-red-400 !text-[3rem] !w-[3rem] !h-[3rem] mb-4"
            >error_outline</mat-icon
          >
          <h2 class="text-xl font-bold mb-2">Invitation invalide</h2>
          <p class="text-gray-400 text-sm mb-6">{{ error() }}</p>
          <a routerLink="/cyberscan" mat-flat-button color="primary">Retour à l'accueil</a>
        } @else if (collab()) {
          <mat-icon class="text-green-400 !text-[3rem] !w-[3rem] !h-[3rem] mb-4"
            >check_circle</mat-icon
          >
          <h2 class="text-xl font-bold mb-2">Invitation acceptée</h2>
          <p class="text-gray-400 text-sm mb-2">
            Vous avez rejoint le site en tant que
            <strong class="text-white">{{ roleLabel(collab()!.role) }}</strong
            >.
          </p>
          <p class="text-gray-500 text-xs mb-6">
            Connectez-vous pour accéder aux résultats de l'audit.
          </p>
          <a routerLink="/cyberscan/dashboard" mat-flat-button color="primary"
            >Accéder au dashboard</a
          >
        }
      </div>
    </div>
  `,
})
export class CollabAcceptComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private collabService = inject(CollabService);
  private title = inject(Title);

  loading = signal(true);
  error = signal<string | null>(null);
  collab = signal<Collaborator | null>(null);

  ngOnInit() {
    this.title.setTitle("Accepter l'invitation — CyberScan");
    const token = this.route.snapshot.paramMap.get('token') ?? '';
    this.collabService.acceptInvite(token).subscribe({
      next: c => {
        this.collab.set(c);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(err.error?.detail || 'Invitation introuvable ou expirée');
        this.loading.set(false);
      },
    });
  }

  roleLabel(role: string): string {
    return { viewer: 'Lecteur', auditor: 'Auditeur', manager: 'Manager' }[role] ?? role;
  }
}
