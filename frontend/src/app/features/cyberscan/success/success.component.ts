import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Title } from '@angular/platform-browser';
import { CyberscanService } from '../services/cyberscan.service';
import { CommonModule } from '@angular/common';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  selector: 'app-checkout-success',
  standalone: true,
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule, NavButtonsComponent],
  template: `
    <div class="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center gap-6 text-center px-8">
      <div class="absolute top-4 left-4">
        <app-nav-buttons />
      </div>
      <div class="w-24 h-24 rounded-full bg-green-500/20 border-2 border-green-500 flex items-center justify-center mb-2">
        <mat-icon class="text-green-400 !text-[3rem] !w-[3rem] !h-[3rem]">check_circle</mat-icon>
      </div>
      <h1 class="text-4xl font-extrabold">Abonnement activé !</h1>
      <p class="text-gray-400 text-xl max-w-md">
        Bienvenue sur CyberScan. Votre plan <span class="text-cyan-400 font-semibold">{{ planName }}</span> est actif.
      </p>
      <div class="flex gap-4 mt-4 flex-wrap justify-center">
        <a routerLink="/cyberscan/onboarding" mat-flat-button color="primary" class="px-8 py-3 text-lg">
          <mat-icon class="mr-1">rocket_launch</mat-icon>
          Démarrer le guide
        </a>
        <a routerLink="/cyberscan/dashboard" mat-stroked-button class="px-8 py-3 text-lg border-gray-600 text-gray-300">
          Dashboard
        </a>
      </div>
      <p class="text-gray-600 text-sm mt-6">Vous recevrez une confirmation par email.</p>
    </div>
  `,
})
export class CheckoutSuccessComponent implements OnInit {
  private cyberscan = inject(CyberscanService);
  private title = inject(Title);
  planName = '';

  ngOnInit() {
    this.title.setTitle('Abonnement activé — CyberScan');
    this.cyberscan.getMySubscription().subscribe({
      next: sub => { this.planName = sub?.plan?.display_name ?? ''; },
    });
  }
}
