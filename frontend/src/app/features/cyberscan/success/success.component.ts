import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { Title } from '@angular/platform-browser';
import { CyberscanService } from '../services/cyberscan.service';
import { CommonModule } from '@angular/common';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    selector: 'app-checkout-success',
    imports: [CommonModule, RouterLink, MatIconModule, NavButtonsComponent],
    template: `
    <div class="min-h-screen bg-gray-900 text-white relative overflow-hidden flex flex-col items-center justify-center px-8">

      <!-- Background -->
      <div class="absolute inset-0 pointer-events-none">
        <div class="auth-dot-grid absolute inset-0 opacity-25"></div>
        <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full"
             style="background: radial-gradient(circle, rgba(74,222,128,0.07) 0%, transparent 65%)"></div>
      </div>

      <!-- Nav -->
      <div class="absolute top-4 left-4">
        <app-nav-buttons />
      </div>

      <!-- Check icon with animated rings -->
      <div class="relative flex items-center justify-center mb-8">
        <div class="absolute w-40 h-40 rounded-full border border-green-500/10 animate-ping"
             style="animation-duration:2.5s"></div>
        <div class="absolute w-32 h-32 rounded-full border border-green-500/20 animate-ping"
             style="animation-duration:2s; animation-delay:0.3s"></div>
        <div class="absolute w-24 h-24 rounded-full border border-green-500/30"></div>
        <div class="relative w-[4.5rem] h-[4.5rem] rounded-full flex items-center justify-center"
             style="background: rgba(74,222,128,0.12); border: 2px solid rgba(74,222,128,0.5); box-shadow: 0 0 32px rgba(74,222,128,0.15)">
          <mat-icon class="text-green-400 !text-[2.2rem] !w-[2.2rem] !h-[2.2rem]">check_circle</mat-icon>
        </div>
      </div>

      <!-- Title -->
      <div class="text-center mb-6 relative z-10">
        <h1 class="text-4xl font-extrabold mb-3 tracking-tight">Abonnement activé&nbsp;!</h1>
        <p class="text-gray-400 text-lg max-w-sm leading-relaxed">
          Bienvenue sur CyberScan. Votre plan
          <span class="text-green-400 font-bold">{{ planName }}</span>
          est désormais actif.
        </p>
      </div>

      <!-- Plan card -->
      <div class="relative z-10 w-full max-w-xs mb-7"
           style="background: rgba(31,41,55,0.6); border: 1px solid rgba(74,222,128,0.2); border-radius: 1rem; padding: 1rem 1.25rem">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
               style="background: rgba(74,222,128,0.12); border: 1px solid rgba(74,222,128,0.25)">
            <mat-icon class="text-green-400 !text-[1.1rem] !w-[1.1rem] !h-[1.1rem]">verified</mat-icon>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-white font-semibold text-sm">Plan {{ planName }}</p>
            <p class="text-gray-400 text-xs">Accès complet débloqué</p>
          </div>
          <span class="text-xs font-bold px-2.5 py-1 rounded-full flex-shrink-0"
                style="background: rgba(74,222,128,0.12); color: #4ade80; border: 1px solid rgba(74,222,128,0.25)">
            Actif
          </span>
        </div>
      </div>

      <!-- Buttons -->
      <div class="relative z-10 flex gap-3 flex-wrap justify-center mb-8">
        <a routerLink="/cyberscan/onboarding"
           class="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all"
           style="background: linear-gradient(135deg,#06b6d4,#0891b2); color:#000; box-shadow: 0 4px 20px rgba(6,182,212,0.3)">
          <mat-icon class="!text-[1rem] !w-[1rem] !h-[1rem]">rocket_launch</mat-icon>
          Démarrer le guide
        </a>
        <a routerLink="/cyberscan/dashboard"
           class="flex items-center gap-2 px-6 py-2.5 rounded-xl border border-gray-700 text-gray-300 text-sm font-semibold hover:border-gray-500 hover:text-white hover:bg-gray-800/60 transition-all">
          <mat-icon class="!text-[1rem] !w-[1rem] !h-[1rem]">dashboard</mat-icon>
          Dashboard
        </a>
      </div>

      <p class="relative z-10 text-gray-600 text-xs">Une confirmation a été envoyée à votre adresse email.</p>

    </div>
  `
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
