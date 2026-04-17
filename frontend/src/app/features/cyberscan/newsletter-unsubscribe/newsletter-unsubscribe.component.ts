import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    standalone: true,
    selector: 'app-newsletter-unsubscribe',
    imports: [RouterLink, MatIconModule, NavButtonsComponent],
    template: `
    <div style="min-height:100vh;background:#0f172a;display:flex;flex-direction:column;">

      <!-- Navbar -->
      <nav style="padding:16px 24px;display:flex;align-items:center;gap:12px;border-bottom:1px solid rgba(255,255,255,0.06);">
        <app-nav-buttons />
        <a routerLink="/cyberscan" style="color:#22d3ee;font-weight:700;font-size:15px;text-decoration:none;margin-left:8px;">
          CyberScan
        </a>
      </nav>

      <!-- Content -->
      <div style="flex:1;display:flex;align-items:center;justify-content:center;padding:40px 24px;">
        <div style="max-width:480px;width:100%;text-align:center;">

          @if (status() === 'ok') {
            <!-- Success -->
            <div style="width:72px;height:72px;border-radius:50%;background:rgba(100,116,139,0.15);border:1px solid rgba(100,116,139,0.3);display:flex;align-items:center;justify-content:center;margin:0 auto 24px;">
              <mat-icon style="color:#94a3b8;font-size:32px;width:32px;height:32px;">unsubscribe</mat-icon>
            </div>
            <p style="color:#67e8f9;font-size:12px;letter-spacing:2px;font-weight:600;margin:0 0 12px;text-transform:uppercase;">
              Radar Cyber
            </p>
            <h1 style="color:#f1f5f9;font-size:28px;font-weight:800;margin:0 0 16px;">
              Désabonnement effectué
            </h1>
            <p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 32px;">
              Vous avez bien été retiré(e) de la liste du Radar Cyber.
              Vous ne recevrez plus nos prochaines éditions.
            </p>

            <!-- Re-subscribe nudge -->
            <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;margin-bottom:24px;">
              <p style="color:#64748b;font-size:13px;margin:0 0 16px;">
                Vous avez changé d'avis ? Vous pouvez vous réabonner à tout moment.
              </p>
              <a routerLink="/cyberscan" fragment="newsletter"
                 style="padding:10px 20px;border-radius:8px;background:rgba(8,145,178,0.15);border:1px solid rgba(8,145,178,0.3);color:#22d3ee;text-decoration:none;font-size:13px;font-weight:600;">
                Se réabonner
              </a>
            </div>

            <a routerLink="/cyberscan"
               style="color:#475569;font-size:13px;text-decoration:none;">
              Retour à l'accueil
            </a>
          }

          @if (status() === 'invalid') {
            <!-- Invalid token -->
            <div style="width:72px;height:72px;border-radius:50%;background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);display:flex;align-items:center;justify-content:center;margin:0 auto 24px;">
              <mat-icon style="color:#f87171;font-size:32px;width:32px;height:32px;">error_outline</mat-icon>
            </div>
            <h1 style="color:#f1f5f9;font-size:26px;font-weight:800;margin:0 0 16px;">
              Lien invalide
            </h1>
            <p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 32px;">
              Ce lien de désabonnement est invalide ou a déjà été utilisé.
            </p>
            <a routerLink="/cyberscan"
               style="padding:12px 24px;border-radius:10px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);color:#94a3b8;text-decoration:none;font-weight:600;font-size:14px;">
              Retour à l'accueil
            </a>
          }

          @if (status() === 'loading') {
            <div style="color:#475569;font-size:15px;">Chargement...</div>
          }

        </div>
      </div>
    </div>
  `
})
export class NewsletterUnsubscribeComponent implements OnInit {
  private route = inject(ActivatedRoute);
  readonly status = signal<'loading' | 'ok' | 'invalid'>('loading');

  ngOnInit() {
    const s = this.route.snapshot.queryParamMap.get('status');
    this.status.set(s === 'ok' ? 'ok' : s === 'invalid' ? 'invalid' : 'loading');
  }
}
