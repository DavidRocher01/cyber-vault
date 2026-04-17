import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
    selector: 'app-not-found',
    imports: [RouterLink, MatButtonModule, MatIconModule],
    template: `
    <div class="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center gap-6 text-center px-8">
      <mat-icon class="!text-[6rem] !w-[6rem] !h-[6rem] text-cyan-400">gpp_bad</mat-icon>
      <h1 class="text-8xl font-extrabold text-cyan-400">404</h1>
      <p class="text-2xl font-semibold">Page introuvable</p>
      <p class="text-gray-400 max-w-md">
        La page que vous cherchez n'existe pas ou a été déplacée.
      </p>
      <a routerLink="/cyberscan" mat-flat-button color="primary" class="px-8 py-3 text-lg">
        Retour à l'accueil
      </a>
    </div>
  `
})
export class NotFoundComponent {}
