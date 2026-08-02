import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { AdminAuthService } from './admin-auth.service';

@Component({
  standalone: true,
  selector: 'app-admin-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet, ReactiveFormsModule, MatIconModule],
  template: `
    @if (auth.verificationEnCours()) {
      <!-- Sans cet etat, l'ecran de cle s'afficherait une fraction de seconde
           avant d'etre remplace : un clignotement a chaque ouverture. -->
      <div class="min-h-screen bg-gray-950 flex items-center justify-center">
        <p class="text-gray-600 text-sm">Vérification de l'accès…</p>
      </div>
    } @else if (!auth.authenticated()) {
      <div class="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <form
          [formGroup]="keyForm"
          (ngSubmit)="login()"
          class="bg-gray-800/50 border border-gray-700 rounded-2xl p-8 w-full max-w-sm space-y-4"
        >
          <div class="flex items-center gap-2 mb-2">
            <mat-icon class="text-cyan-400">admin_panel_settings</mat-icon>
            <h1 class="text-white font-bold text-lg">Administration Rocher Cybersécurité</h1>
          </div>
          <p class="text-gray-500 text-xs leading-relaxed">
            Connectez-vous avec un compte administrateur pour accéder au back-office. La clé
            ci-dessous est un accès de secours, appelé à disparaître.
          </p>
          <input
            formControlName="key"
            type="password"
            placeholder="Clé admin"
            class="w-full px-4 py-2.5 rounded-lg bg-gray-900 border text-white text-sm outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            [class.border-gray-600]="!(keyForm.get('key')?.invalid && keyForm.get('key')?.touched)"
            [class.border-red-500]="keyForm.get('key')?.invalid && keyForm.get('key')?.touched"
          />
          @if (keyForm.get('key')?.invalid && keyForm.get('key')?.touched) {
            <p class="mt-1 text-xs text-red-400">La clé est requise.</p>
          }
          @if (authError()) {
            <p class="text-red-400 text-sm">{{ authError() }}</p>
          }
          <button
            type="submit"
            [disabled]="verifying()"
            class="w-full py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-sm transition-all disabled:opacity-50"
          >
            {{ verifying() ? 'Vérification...' : 'Connexion' }}
          </button>
        </form>
      </div>
    } @else {
      <div class="min-h-screen bg-gray-950 flex">
        <!-- Sidebar -->
        <aside class="w-56 bg-gray-900 border-r border-gray-800 flex flex-col shrink-0">
          <div class="px-5 py-4 border-b border-gray-800">
            <div class="flex items-center gap-2">
              <mat-icon class="text-cyan-400 text-base">admin_panel_settings</mat-icon>
              <span class="text-white font-semibold text-sm">Admin</span>
            </div>
          </div>
          <nav class="flex-1 px-3 py-4 space-y-1 text-sm">
            @for (item of navItems; track item.path) {
              <a
                [routerLink]="item.path"
                routerLinkActive="bg-cyan-900/30 text-cyan-400 border-cyan-800"
                [routerLinkActiveOptions]="{ exact: item.exact }"
                class="flex items-center gap-2.5 px-3 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors border border-transparent"
              >
                <mat-icon class="text-base !h-4 !w-4">{{ item.icon }}</mat-icon>
                {{ item.label }}
              </a>
            }
          </nav>
          <div class="px-3 py-4 border-t border-gray-800 space-y-1">
            @if (auth.parCompte()) {
              <p class="px-3 pb-2 text-[11px] text-gray-600 leading-relaxed">
                Connecté par compte administrateur
              </p>
            }
            <button
              type="button"
              (click)="auth.logout()"
              class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-gray-500 hover:text-red-400 hover:bg-gray-800 transition-colors text-sm"
            >
              <mat-icon class="text-base !h-4 !w-4">logout</mat-icon>
              Déconnexion
            </button>
          </div>
        </aside>

        <!-- Content -->
        <main class="flex-1 overflow-auto">
          <router-outlet />
        </main>
      </div>
    }
  `,
})
export class AdminShellComponent implements OnInit {
  auth = inject(AdminAuthService);
  private fb = inject(FormBuilder);

  verifying = signal(false);
  authError = signal('');

  keyForm = this.fb.group({ key: ['', Validators.required] });

  ngOnInit(): void {
    // Un compte administrateur entre sans rien saisir. Un echec n'est pas une
    // erreur : la plupart des visiteurs de /admin ne sont pas connectes, on
    // retombe alors sur la cle de secours.
    this.auth.verifierCompte().subscribe();
  }

  navItems = [
    { path: '/admin', label: "Vue d'ensemble", icon: 'dashboard', exact: true },
    { path: '/admin/contacts', label: 'Contacts', icon: 'mail_outline', exact: false },
    { path: '/admin/blog', label: 'Blog', icon: 'article', exact: false },
    { path: '/admin/users', label: 'Utilisateurs', icon: 'people', exact: false },
    { path: '/admin/scans', label: 'Scans publics', icon: 'radar', exact: false },
    { path: '/admin/invoices', label: 'Factures', icon: 'receipt_long', exact: false },
    { path: '/admin/quotes', label: 'Devis', icon: 'request_quote', exact: false },
    { path: '/admin/acquisition', label: 'Acquisition', icon: 'trending_up', exact: false },
    // Agenda et Newsletter etaient codes en dur sous la liste, dans un bloc a
    // part : plus ternes, et surtout SANS routerLinkActive, donc ils ne
    // s'allumaient jamais quand on etait dessus. Rapatries ici, ils se
    // comportent comme les autres.
    { path: '/admin/ba61c5a60113/agenda', label: 'Agenda', icon: 'calendar_month', exact: false },
    { path: '/admin/newsletter', label: 'Newsletter', icon: 'mail', exact: false },
  ];

  login() {
    if (this.keyForm.invalid) {
      this.keyForm.markAllAsTouched();
      return;
    }
    const key = this.keyForm.value.key ?? '';
    this.authError.set('');
    this.verifying.set(true);
    this.auth.verify(key).subscribe({
      next: () => {
        this.auth.login(key);
        this.verifying.set(false);
      },
      error: () => {
        this.authError.set('Clé admin incorrecte.');
        this.verifying.set(false);
      },
    });
  }
}
