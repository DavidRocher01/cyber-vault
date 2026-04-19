import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { environment } from '../../../../environments/environment';

interface Stats { total: number; active: number; pending_confirmation: number; }

@Component({
  standalone: true,
  selector: 'app-newsletter-admin',
  imports: [ReactiveFormsModule, RouterLink, MatIconModule, NavButtonsComponent],
  template: `
  <div style="min-height:100vh;background:#0f172a;font-family:Arial,sans-serif;">

    <!-- Navbar -->
    <nav style="padding:16px 24px;display:flex;align-items:center;gap:12px;border-bottom:1px solid rgba(255,255,255,0.06);">
      <app-nav-buttons />
      <a routerLink="/cyberscan" style="color:#22d3ee;font-weight:700;font-size:15px;text-decoration:none;margin-left:8px;">CyberScan</a>
      <span style="color:#334155;margin:0 4px;">/</span>
      <span style="color:#64748b;font-size:14px;">Admin Newsletter</span>
    </nav>

    <div style="max-width:760px;margin:0 auto;padding:40px 24px;">

      <!-- Clé admin -->
      @if (!apiKeySet()) {
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;text-align:center;">
          <mat-icon style="font-size:40px;width:40px;height:40px;color:#f59e0b;margin-bottom:16px;">lock</mat-icon>
          <h2 style="color:#f1f5f9;margin:0 0 8px;">Accès admin requis</h2>
          <p style="color:#64748b;font-size:14px;margin:0 0 24px;">Entrez votre clé admin pour accéder au tableau de bord newsletter.</p>
          <form (ngSubmit)="submitKey()" style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
            <input type="password" [(ngModel)]="keyInput" [ngModelOptions]="{standalone:true}"
              placeholder="Admin API Key"
              style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;color:#f1f5f9;font-size:14px;width:280px;outline:none;">
            <button type="submit"
              style="background:#0891b2;color:#fff;border:none;border-radius:8px;padding:10px 24px;font-size:14px;font-weight:600;cursor:pointer;">
              Valider
            </button>
          </form>
          @if (keyError()) {
            <p style="color:#f87171;font-size:13px;margin:12px 0 0;">Clé invalide ou erreur réseau.</p>
          }
        </div>
      }

      @if (apiKeySet()) {
        <!-- Stats -->
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:32px;">
          <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px;text-align:center;">
            <p style="margin:0 0 4px;font-size:28px;font-weight:800;color:#f1f5f9;">{{ stats()?.total ?? '…' }}</p>
            <p style="margin:0;color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Total inscrits</p>
          </div>
          <div style="background:#1e293b;border:1px solid #22d3ee33;border-radius:12px;padding:20px;text-align:center;">
            <p style="margin:0 0 4px;font-size:28px;font-weight:800;color:#22d3ee;">{{ stats()?.active ?? '…' }}</p>
            <p style="margin:0;color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Abonnés actifs</p>
          </div>
          <div style="background:#1e293b;border:1px solid #f59e0b33;border-radius:12px;padding:20px;text-align:center;">
            <p style="margin:0 0 4px;font-size:28px;font-weight:800;color:#f59e0b;">{{ stats()?.pending_confirmation ?? '…' }}</p>
            <p style="margin:0;color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:1px;">En attente</p>
          </div>
        </div>

        <!-- Formulaire édition -->
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;">
          <h2 style="color:#f1f5f9;margin:0 0 4px;font-size:20px;">Envoyer une édition</h2>
          <p style="color:#64748b;font-size:13px;margin:0 0 28px;">Sera envoyée aux <strong style="color:#22d3ee;">{{ stats()?.active ?? '?' }} abonnés actifs</strong>.</p>

          <form [formGroup]="form" (ngSubmit)="sendIssue()">

            <!-- Numéro d'édition -->
            <div style="margin-bottom:20px;">
              <label style="display:block;color:#94a3b8;font-size:12px;font-weight:600;letter-spacing:1px;margin-bottom:6px;">NUMÉRO D'ÉDITION</label>
              <input type="number" formControlName="edition"
                style="width:100%;box-sizing:border-box;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;outline:none;">
            </div>

            <!-- Flash international -->
            <div style="border-left:3px solid #ef4444;padding-left:16px;margin-bottom:24px;">
              <p style="color:#ef4444;font-size:11px;font-weight:700;letter-spacing:1px;margin:0 0 12px;">🌍 FLASH INTERNATIONAL</p>
              <div style="margin-bottom:12px;">
                <label style="display:block;color:#94a3b8;font-size:12px;margin-bottom:6px;">Titre</label>
                <input type="text" formControlName="flash_title" placeholder="Ex: Campagne ransomware vise les PME européennes"
                  style="width:100%;box-sizing:border-box;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;outline:none;">
              </div>
              <div>
                <label style="display:block;color:#94a3b8;font-size:12px;margin-bottom:6px;">Corps</label>
                <textarea formControlName="flash_body" rows="4" placeholder="Résumé de l'attaque, contexte, impact..."
                  style="width:100%;box-sizing:border-box;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;outline:none;resize:vertical;"></textarea>
              </div>
            </div>

            <!-- Le bon réflexe -->
            <div style="border-left:3px solid #22d3ee;padding-left:16px;margin-bottom:24px;">
              <p style="color:#22d3ee;font-size:11px;font-weight:700;letter-spacing:1px;margin:0 0 12px;">💡 LE BON RÉFLEXE</p>
              <div style="margin-bottom:12px;">
                <label style="display:block;color:#94a3b8;font-size:12px;margin-bottom:6px;">Titre</label>
                <input type="text" formControlName="reflex_title" placeholder="Ex: Activez l'authentification à deux facteurs"
                  style="width:100%;box-sizing:border-box;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;outline:none;">
              </div>
              <div>
                <label style="display:block;color:#94a3b8;font-size:12px;margin-bottom:6px;">Corps</label>
                <textarea formControlName="reflex_body" rows="4" placeholder="Explication du conseil en 2-3 phrases..."
                  style="width:100%;box-sizing:border-box;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;outline:none;resize:vertical;"></textarea>
              </div>
            </div>

            <!-- Coin dirigeants -->
            <div style="border-left:3px solid #a855f7;padding-left:16px;margin-bottom:32px;">
              <p style="color:#a855f7;font-size:11px;font-weight:700;letter-spacing:1px;margin:0 0 12px;">⚖️ COIN DES DIRIGEANTS</p>
              <div style="margin-bottom:12px;">
                <label style="display:block;color:#94a3b8;font-size:12px;margin-bottom:6px;">Titre</label>
                <input type="text" formControlName="legal_title" placeholder="Ex: NIS2 — les PME ont jusqu'au 17 octobre"
                  style="width:100%;box-sizing:border-box;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;outline:none;">
              </div>
              <div>
                <label style="display:block;color:#94a3b8;font-size:12px;margin-bottom:6px;">Corps</label>
                <textarea formControlName="legal_body" rows="4" placeholder="Point réglementaire ou conformité..."
                  style="width:100%;box-sizing:border-box;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;outline:none;resize:vertical;"></textarea>
              </div>
            </div>

            <!-- Actions -->
            @if (sendResult()) {
              <div [style.background]="sendResult()!.ok ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)'"
                   [style.border]="sendResult()!.ok ? '1px solid rgba(34,197,94,0.3)' : '1px solid rgba(239,68,68,0.3)'"
                   style="border-radius:8px;padding:14px 16px;margin-bottom:20px;display:flex;align-items:center;gap:10px;">
                <mat-icon [style.color]="sendResult()!.ok ? '#4ade80' : '#f87171'">
                  {{ sendResult()!.ok ? 'check_circle' : 'error_outline' }}
                </mat-icon>
                <span [style.color]="sendResult()!.ok ? '#4ade80' : '#f87171'" style="font-size:14px;">{{ sendResult()!.message }}</span>
              </div>
            }

            <button type="submit" [disabled]="form.invalid || sending()"
              style="width:100%;background:linear-gradient(135deg,#0891b2,#0e7490);color:#fff;border:none;border-radius:10px;padding:14px;font-size:15px;font-weight:700;cursor:pointer;opacity:1;"
              [style.opacity]="form.invalid || sending() ? '0.5' : '1'">
              @if (sending()) { Envoi en cours… } @else { Envoyer l'édition #{{ form.value.edition }} }
            </button>

          </form>
        </div>

        <!-- Déconnexion admin -->
        <div style="text-align:center;margin-top:20px;">
          <button (click)="logout()" style="background:none;border:none;color:#475569;font-size:13px;cursor:pointer;text-decoration:underline;">
            Changer de clé admin
          </button>
        </div>
      }

    </div>
  </div>
  `,
})
export class NewsletterAdminComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  apiKeySet = signal(false);
  keyInput = '';
  keyError = signal(false);
  stats = signal<Stats | null>(null);
  sending = signal(false);
  sendResult = signal<{ ok: boolean; message: string } | null>(null);

  form = this.fb.nonNullable.group({
    edition:      [1,    Validators.required],
    flash_title:  ['',   Validators.required],
    flash_body:   ['',   Validators.required],
    reflex_title: ['',   Validators.required],
    reflex_body:  ['',   Validators.required],
    legal_title:  ['',   Validators.required],
    legal_body:   ['',   Validators.required],
  });

  ngOnInit() {
    const saved = sessionStorage.getItem('admin_key');
    if (saved) { this.apiKeySet.set(true); this.keyInput = saved; this.loadStats(); }
  }

  submitKey() {
    this.keyError.set(false);
    const headers = new HttpHeaders({ 'X-Admin-Key': this.keyInput });
    this.http.get<Stats>(`${environment.apiUrl}/newsletter/admin/stats`, { headers }).subscribe({
      next: data => {
        sessionStorage.setItem('admin_key', this.keyInput);
        this.apiKeySet.set(true);
        this.stats.set(data);
      },
      error: () => this.keyError.set(true),
    });
  }

  loadStats() {
    const headers = new HttpHeaders({ 'X-Admin-Key': this.keyInput });
    this.http.get<Stats>(`${environment.apiUrl}/newsletter/admin/stats`, { headers }).subscribe({
      next: data => this.stats.set(data),
    });
  }

  sendIssue() {
    if (this.form.invalid) return;
    this.sending.set(true);
    this.sendResult.set(null);
    const headers = new HttpHeaders({ 'X-Admin-Key': this.keyInput });
    this.http.post<{ sent: number; message: string }>(
      `${environment.apiUrl}/newsletter/admin/send-issue`,
      this.form.getRawValue(),
      { headers }
    ).subscribe({
      next: res => {
        this.sending.set(false);
        this.sendResult.set({ ok: true, message: res.message });
        this.loadStats();
      },
      error: () => {
        this.sending.set(false);
        this.sendResult.set({ ok: false, message: "Erreur lors de l'envoi. Vérifiez la clé admin." });
      },
    });
  }

  logout() {
    sessionStorage.removeItem('admin_key');
    this.apiKeySet.set(false);
    this.keyInput = '';
    this.stats.set(null);
  }
}
