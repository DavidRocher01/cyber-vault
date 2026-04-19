import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { FormArray, FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { environment } from '../../../../environments/environment';

interface Stats { total: number; active: number; pending_confirmation: number; }
interface Article { position: number; actu_title: string; actu_url: string; actu_source: string; reflex: string; image_url?: string | null; }

const ACCENT = ['#ef4444','#f97316','#eab308','#22c55e','#3b82f6','#a855f7'];

@Component({
  standalone: true,
  selector: 'app-newsletter-admin',
  imports: [ReactiveFormsModule, FormsModule, RouterLink, MatIconModule, NavButtonsComponent],
  template: `
  <div style="min-height:100vh;background:#0f172a;font-family:Arial,sans-serif;">

    <!-- Navbar -->
    <nav style="padding:16px 24px;display:flex;align-items:center;gap:12px;border-bottom:1px solid rgba(255,255,255,0.06);">
      <app-nav-buttons />
      <a routerLink="/cyberscan" style="color:#22d3ee;font-weight:700;font-size:15px;text-decoration:none;margin-left:8px;">CyberScan</a>
      <span style="color:#334155;margin:0 4px;">/</span>
      <span style="color:#64748b;font-size:14px;">Admin Newsletter</span>
    </nav>

    <div style="max-width:820px;margin:0 auto;padding:40px 24px;">

      <!-- Clé admin -->
      @if (!apiKeySet()) {
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;text-align:center;">
          <mat-icon style="font-size:40px;width:40px;height:40px;color:#f59e0b;margin-bottom:16px;">lock</mat-icon>
          <h2 style="color:#f1f5f9;margin:0 0 8px;">Accès admin requis</h2>
          <p style="color:#64748b;font-size:14px;margin:0 0 24px;">Entrez votre clé admin pour continuer.</p>
          <form (ngSubmit)="submitKey()" style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
            <input type="password" [(ngModel)]="keyInput" [ngModelOptions]="{standalone:true}" placeholder="Admin API Key"
              style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 16px;color:#f1f5f9;font-size:14px;width:280px;outline:none;">
            <button type="submit" style="background:#0891b2;color:#fff;border:none;border-radius:8px;padding:10px 24px;font-size:14px;font-weight:600;cursor:pointer;">
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

        <!-- Planning — 6 slots -->
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;margin-bottom:24px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;">
            <div>
              <h2 style="color:#f1f5f9;margin:0 0 4px;font-size:20px;">Planning de l'édition</h2>
              <p style="color:#64748b;font-size:13px;margin:0;">Remplissez les articles puis enregistrez.</p>
            </div>
            <button (click)="saveSchedule()" [disabled]="scheduleForm.invalid || savingSchedule()"
              style="background:#0891b2;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap;"
              [style.opacity]="savingSchedule() ? '0.5' : '1'">
              @if (savingSchedule()) { Enregistrement… } @else { Enregistrer le planning }
            </button>
          </div>

          @if (saveOk()) {
            <div style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);border-radius:8px;padding:12px 16px;margin-bottom:20px;display:flex;align-items:center;gap:8px;">
              <mat-icon style="color:#4ade80;font-size:18px;width:18px;height:18px;">check_circle</mat-icon>
              <span style="color:#4ade80;font-size:13px;">Planning enregistré avec succès.</span>
            </div>
          }

          <form [formGroup]="scheduleForm">
            <div formArrayName="articles">
              @for (ctrl of articleControls; track $index) {
                <div [formGroupName]="$index"
                  style="border:1px solid #1e293b;border-radius:10px;padding:20px;margin-bottom:16px;background:#0f172a;">

                  <!-- En-tête slot -->
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
                    <span [style.background]="accent($index) + '22'" [style.color]="accent($index)"
                      style="font-size:11px;font-weight:800;letter-spacing:2px;padding:4px 12px;border-radius:20px;">
                      ARTICLE {{ $index + 1 }}
                    </span>
                  </div>

                  <!-- Ligne 1 : source + URL image -->
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
                    <div>
                      <label style="display:block;color:#475569;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px;">SOURCE</label>
                      <input formControlName="actu_source" placeholder="Ex: BleepingComputer"
                        style="width:100%;box-sizing:border-box;background:#1e293b;border:1px solid #334155;border-radius:6px;padding:9px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                    </div>
                    <div>
                      <label style="display:block;color:#475569;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px;">URL IMAGE <span style="color:#334155;">(optionnel)</span></label>
                      <input formControlName="image_url" placeholder="https://..."
                        style="width:100%;box-sizing:border-box;background:#1e293b;border:1px solid #334155;border-radius:6px;padding:9px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                    </div>
                  </div>

                  <!-- Ligne 2 : titre -->
                  <div style="margin-bottom:10px;">
                    <label style="display:block;color:#475569;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px;">TITRE DE L'ARTICLE</label>
                    <input formControlName="actu_title" placeholder="Ex: Campagne ransomware vise les PME européennes"
                      style="width:100%;box-sizing:border-box;background:#1e293b;border:1px solid #334155;border-radius:6px;padding:9px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                  </div>

                  <!-- Ligne 3 : URL article -->
                  <div style="margin-bottom:10px;">
                    <label style="display:block;color:#475569;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px;">URL DE L'ARTICLE</label>
                    <input formControlName="actu_url" placeholder="https://..."
                      style="width:100%;box-sizing:border-box;background:#1e293b;border:1px solid #334155;border-radius:6px;padding:9px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                  </div>

                  <!-- Ligne 4 : note -->
                  <div>
                    <label style="display:block;color:#475569;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:4px;">NOTE (pourquoi lire cet article ?)</label>
                    <input formControlName="reflex" placeholder="Ex: Réduire le délai de détection grâce à un EDR/SIEM"
                      style="width:100%;box-sizing:border-box;background:#1e293b;border:1px solid #334155;border-radius:6px;padding:9px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                  </div>

                </div>
              }
            </div>
          </form>
        </div>

        <!-- Envoyer -->
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;">
          <h2 style="color:#f1f5f9;margin:0 0 4px;font-size:20px;">Envoyer l'édition</h2>
          <p style="color:#64748b;font-size:13px;margin:0 0 20px;">
            Sera envoyée aux <strong style="color:#22d3ee;">{{ stats()?.active ?? '?' }} abonnés actifs</strong>.
          </p>
          <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;">
            <div>
              <label style="display:block;color:#475569;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:6px;">NUMÉRO D'ÉDITION</label>
              <input type="number" [(ngModel)]="editionNumber"
                style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;outline:none;width:100px;">
            </div>
            <button (click)="sendFromSchedule()" [disabled]="sending()"
              style="background:linear-gradient(135deg,#0891b2,#0e7490);color:#fff;border:none;border-radius:10px;padding:12px 28px;font-size:14px;font-weight:700;cursor:pointer;"
              [style.opacity]="sending() ? '0.5' : '1'">
              @if (sending()) { Envoi en cours… } @else { Envoyer l'édition #{{ editionNumber }} }
            </button>
          </div>

          @if (sendResult()) {
            <div [style.background]="sendResult()!.ok ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)'"
                 [style.border]="sendResult()!.ok ? '1px solid rgba(34,197,94,0.3)' : '1px solid rgba(239,68,68,0.3)'"
                 style="border-radius:8px;padding:14px 16px;margin-top:20px;display:flex;align-items:center;gap:10px;">
              <mat-icon [style.color]="sendResult()!.ok ? '#4ade80' : '#f87171'">
                {{ sendResult()!.ok ? 'check_circle' : 'error_outline' }}
              </mat-icon>
              <span [style.color]="sendResult()!.ok ? '#4ade80' : '#f87171'" style="font-size:14px;">{{ sendResult()!.message }}</span>
            </div>
          }
        </div>

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
  private fb   = inject(FormBuilder);

  apiKeySet     = signal(false);
  keyInput      = '';
  keyError      = signal(false);
  stats         = signal<Stats | null>(null);
  sending       = signal(false);
  savingSchedule = signal(false);
  saveOk        = signal(false);
  sendResult    = signal<{ ok: boolean; message: string } | null>(null);
  editionNumber = 1;

  scheduleForm = this.fb.group({
    articles: this.fb.array(Array.from({ length: 6 }, (_, i) => this._blankSlot(i + 1))),
  });

  get articleControls() {
    return (this.scheduleForm.get('articles') as FormArray).controls;
  }

  accent(i: number) { return ACCENT[i % ACCENT.length]; }

  private _blankSlot(position: number) {
    return this.fb.group({
      position:    [position],
      actu_source: [''],
      actu_title:  [''],
      actu_url:    [''],
      reflex:      [''],
      image_url:   [null as string | null],
    });
  }

  ngOnInit() {
    const saved = sessionStorage.getItem('admin_key');
    if (saved) { this.apiKeySet.set(true); this.keyInput = saved; this.loadStats(); this.loadSchedule(); }
  }

  private headers() { return new HttpHeaders({ 'X-Admin-Key': this.keyInput }); }

  submitKey() {
    this.keyError.set(false);
    this.http.get<Stats>(`${environment.apiUrl}/newsletter/admin/stats`, { headers: this.headers() }).subscribe({
      next: data => {
        sessionStorage.setItem('admin_key', this.keyInput);
        this.apiKeySet.set(true);
        this.stats.set(data);
        this.loadSchedule();
      },
      error: () => this.keyError.set(true),
    });
  }

  loadStats() {
    this.http.get<Stats>(`${environment.apiUrl}/newsletter/admin/stats`, { headers: this.headers() }).subscribe({
      next: data => this.stats.set(data),
    });
  }

  loadSchedule() {
    this.http.get<Article[]>(`${environment.apiUrl}/newsletter/schedule`).subscribe({
      next: articles => {
        const arr = this.scheduleForm.get('articles') as FormArray;
        arr.controls.forEach((ctrl, i) => {
          const pos = i + 1;
          const a = articles.find(x => x.position === pos);
          ctrl.patchValue(a ? { ...a } : { position: pos, actu_source: '', actu_title: '', actu_url: '', reflex: '', image_url: null });
        });
      },
    });
  }

  saveSchedule() {
    this.savingSchedule.set(true);
    this.saveOk.set(false);
    const items = (this.scheduleForm.get('articles') as FormArray).getRawValue()
      .filter((a: Article) => a.actu_title && a.actu_url && a.actu_source && a.reflex);
    this.http.put<Article[]>(`${environment.apiUrl}/newsletter/admin/schedule`, items, { headers: this.headers() }).subscribe({
      next: () => { this.savingSchedule.set(false); this.saveOk.set(true); },
      error: () => this.savingSchedule.set(false),
    });
  }

  sendFromSchedule() {
    this.sending.set(true);
    this.sendResult.set(null);
    this.http.post<{ sent: number; message: string }>(
      `${environment.apiUrl}/newsletter/admin/send-from-schedule`,
      { edition: this.editionNumber },
      { headers: this.headers() }
    ).subscribe({
      next: res => { this.sending.set(false); this.sendResult.set({ ok: true, message: res.message }); },
      error: () => { this.sending.set(false); this.sendResult.set({ ok: false, message: "Erreur lors de l'envoi." }); },
    });
  }

  logout() {
    sessionStorage.removeItem('admin_key');
    this.apiKeySet.set(false);
    this.keyInput = '';
    this.stats.set(null);
  }
}
