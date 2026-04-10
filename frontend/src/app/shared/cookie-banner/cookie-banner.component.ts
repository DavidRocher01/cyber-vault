import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

const STORAGE_KEY = 'cyberscan_cookie_consent';

@Component({
  selector: 'app-cookie-banner',
  standalone: true,
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule],
  template: `
    @if (visible()) {
      <div class="fixed bottom-0 left-0 right-0 z-50 p-4 md:p-6 bg-gray-900/95 border-t border-gray-700 backdrop-blur-sm">
        <div class="max-w-5xl mx-auto flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <mat-icon class="text-cyan-400 flex-shrink-0 hidden sm:block">cookie</mat-icon>
          <div class="flex-1 text-sm text-gray-300">
            <span class="font-semibold text-white">Cookies & confidentialité</span> —
            Nous utilisons uniquement des cookies strictement nécessaires au fonctionnement du service (session, authentification).
            Aucun cookie publicitaire ou de tracking tiers.
            <a routerLink="/cyberscan/politique-confidentialite" class="text-cyan-400 hover:underline ml-1">
              Politique de confidentialité
            </a>
          </div>
          <div class="flex gap-3 flex-shrink-0">
            <button mat-stroked-button (click)="reject()"
                    class="!border-gray-600 !text-gray-400 !text-xs">
              Refuser
            </button>
            <button mat-flat-button (click)="accept()"
                    class="!bg-cyan-500 !text-gray-900 !font-bold !text-xs">
              Accepter
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class CookieBannerComponent {
  visible = signal(false);

  constructor() {
    const consent = localStorage.getItem(STORAGE_KEY);
    if (!consent) {
      this.visible.set(true);
    }
  }

  accept() {
    localStorage.setItem(STORAGE_KEY, 'accepted');
    this.visible.set(false);
  }

  reject() {
    localStorage.setItem(STORAGE_KEY, 'rejected');
    this.visible.set(false);
  }
}
