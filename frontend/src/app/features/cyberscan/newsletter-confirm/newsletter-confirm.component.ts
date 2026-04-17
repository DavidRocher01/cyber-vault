import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    standalone: true,
    selector: 'app-newsletter-confirm',
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
            <div style="width:72px;height:72px;border-radius:50%;background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);display:flex;align-items:center;justify-content:center;margin:0 auto 24px;">
              <mat-icon style="color:#4ade80;font-size:32px;width:32px;height:32px;">check_circle</mat-icon>
            </div>
            <p style="color:#67e8f9;font-size:12px;letter-spacing:2px;font-weight:600;margin:0 0 12px;text-transform:uppercase;">
              Radar Cyber
            </p>
            <h1 style="color:#f1f5f9;font-size:28px;font-weight:800;margin:0 0 16px;">
              Inscription confirmée !
            </h1>
            <p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 32px;">
              Bienvenue dans la communauté. Vous allez recevoir un email de bienvenue dans quelques instants.
              La prochaine édition du Radar Cyber arrive dans moins de deux semaines.
            </p>
            <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
              <a routerLink="/cyberscan"
                 style="padding:12px 24px;border-radius:10px;background:linear-gradient(135deg,#0891b2,#0e7490);color:#fff;text-decoration:none;font-weight:600;font-size:14px;">
                Retour à l'accueil
              </a>
              <a routerLink="/cyberscan/ressources"
                 style="padding:12px 24px;border-radius:10px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);color:#94a3b8;text-decoration:none;font-weight:600;font-size:14px;">
                Voir les ressources
              </a>
            </div>
          }

          @if (status() === 'invalid') {
            <!-- Invalid token -->
            <div style="width:72px;height:72px;border-radius:50%;background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);display:flex;align-items:center;justify-content:center;margin:0 auto 24px;">
              <mat-icon style="color:#f87171;font-size:32px;width:32px;height:32px;">error_outline</mat-icon>
            </div>
            <h1 style="color:#f1f5f9;font-size:26px;font-weight:800;margin:0 0 16px;">
              Lien invalide ou expiré
            </h1>
            <p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 32px;">
              Ce lien de confirmation n'est plus valide. Il a peut-être déjà été utilisé ou a expiré (7 jours).
              Vous pouvez vous réinscrire pour recevoir un nouveau lien.
            </p>
            <a routerLink="/cyberscan" fragment="newsletter"
               style="padding:12px 24px;border-radius:10px;background:linear-gradient(135deg,#0891b2,#0e7490);color:#fff;text-decoration:none;font-weight:600;font-size:14px;">
              Se réinscrire
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
export class NewsletterConfirmComponent implements OnInit {
  private route = inject(ActivatedRoute);
  readonly status = signal<'loading' | 'ok' | 'invalid'>('loading');

  ngOnInit() {
    const s = this.route.snapshot.queryParamMap.get('status');
    this.status.set(s === 'ok' ? 'ok' : s === 'invalid' ? 'invalid' : 'loading');
  }
}
