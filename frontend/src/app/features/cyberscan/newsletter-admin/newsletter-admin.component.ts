import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { environment } from '../../../../environments/environment';

interface Stats { total: number; active: number; pending_confirmation: number; }
interface Article { position: number; actu_title: string; actu_url: string; actu_source: string; reflex: string; image_url?: string | null; }

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

    <div style="max-width:800px;margin:0 auto;padding:40px 24px;">

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

        <!-- Liste des articles -->
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;margin-bottom:24px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
            <div>
              <h2 style="color:#f1f5f9;margin:0 0 4px;font-size:20px;">Articles de l'édition</h2>
              <p style="color:#64748b;font-size:13px;margin:0;">{{ articles().length }}/6 articles · <a href="#" (click)="loadSchedule();$event.preventDefault()" style="color:#22d3ee;text-decoration:none;">Actualiser</a></p>
            </div>
            @if (articles().length < 6) {
              <button (click)="startAdd()"
                style="background:#0891b2;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:6px;">
                <mat-icon style="font-size:16px;width:16px;height:16px;">add</mat-icon> Ajouter
              </button>
            }
          </div>

          <!-- Articles existants -->
          @for (a of articles(); track a.position) {
            <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:16px;margin-bottom:12px;">
              @if (editingPosition() === a.position) {
                <!-- Formulaire édition inline -->
                <form [formGroup]="articleForm" (ngSubmit)="saveArticle(a.position)" style="display:flex;flex-direction:column;gap:10px;">
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                    <input formControlName="actu_source" placeholder="Source (ex: BleepingComputer)"
                      style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                    <input type="number" formControlName="position" placeholder="Position (1-6)"
                      style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                  </div>
                  <input formControlName="actu_title" placeholder="Titre de l'article"
                    style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                  <input formControlName="actu_url" placeholder="URL de l'article"
                    style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                  <input formControlName="reflex" placeholder="Note courte (pourquoi lire cet article ?)"
                    style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                  <input formControlName="image_url" placeholder="URL image (optionnel — ex: https://site.com/image.jpg)"
                    style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                  <div style="display:flex;gap:8px;">
                    <button type="submit" [disabled]="articleForm.invalid"
                      style="background:#0891b2;color:#fff;border:none;border-radius:6px;padding:8px 20px;font-size:13px;font-weight:600;cursor:pointer;">
                      Enregistrer
                    </button>
                    <button type="button" (click)="cancelEdit()"
                      style="background:#1e293b;color:#94a3b8;border:1px solid #334155;border-radius:6px;padding:8px 16px;font-size:13px;cursor:pointer;">
                      Annuler
                    </button>
                  </div>
                </form>
              } @else {
                <div style="display:flex;align-items:flex-start;gap:12px;">
                  <span style="background:#22d3ee22;color:#22d3ee;border-radius:6px;padding:4px 10px;font-size:12px;font-weight:700;white-space:nowrap;">
                    #{{ a.position }}
                  </span>
                  <div style="flex:1;min-width:0;">
                    <p style="margin:0 0 2px;color:#475569;font-size:11px;font-weight:600;letter-spacing:1px;">{{ a.actu_source }}</p>
                    <p style="margin:0 0 4px;color:#f1f5f9;font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{{ a.actu_title }}</p>
                    <p style="margin:0;color:#64748b;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{{ a.reflex }}</p>
                  </div>
                  <div style="display:flex;gap:4px;flex-shrink:0;">
                    <button (click)="startEdit(a)"
                      style="background:none;border:1px solid #334155;border-radius:6px;padding:6px;cursor:pointer;color:#94a3b8;display:flex;align-items:center;">
                      <mat-icon style="font-size:15px;width:15px;height:15px;">edit</mat-icon>
                    </button>
                    <button (click)="deleteArticle(a.position)"
                      style="background:none;border:1px solid #334155;border-radius:6px;padding:6px;cursor:pointer;color:#f87171;display:flex;align-items:center;">
                      <mat-icon style="font-size:15px;width:15px;height:15px;">delete</mat-icon>
                    </button>
                  </div>
                </div>
              }
            </div>
          }

          <!-- Formulaire ajout -->
          @if (adding()) {
            <div style="background:#0f172a;border:1px dashed #334155;border-radius:10px;padding:16px;margin-bottom:12px;">
              <p style="color:#22d3ee;font-size:12px;font-weight:600;margin:0 0 12px;">Nouvel article</p>
              <form [formGroup]="articleForm" (ngSubmit)="saveNewArticle()" style="display:flex;flex-direction:column;gap:10px;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                  <input formControlName="actu_source" placeholder="Source (ex: BleepingComputer)"
                    style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                  <input type="number" formControlName="position" placeholder="Position (1-6)"
                    style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                </div>
                <input formControlName="actu_title" placeholder="Titre de l'article"
                  style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                <input formControlName="actu_url" placeholder="URL de l'article"
                  style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                <input formControlName="reflex" placeholder="Note courte (pourquoi lire cet article ?)"
                  style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                <input formControlName="image_url" placeholder="URL image (optionnel — ex: https://site.com/image.jpg)"
                  style="background:#1e293b;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#f1f5f9;font-size:13px;outline:none;">
                <div style="display:flex;gap:8px;">
                  <button type="submit" [disabled]="articleForm.invalid"
                    style="background:#0891b2;color:#fff;border:none;border-radius:6px;padding:8px 20px;font-size:13px;font-weight:600;cursor:pointer;">
                    Ajouter
                  </button>
                  <button type="button" (click)="cancelEdit()"
                    style="background:#1e293b;color:#94a3b8;border:1px solid #334155;border-radius:6px;padding:8px 16px;font-size:13px;cursor:pointer;">
                    Annuler
                  </button>
                </div>
              </form>
            </div>
          }

          @if (articles().length === 0 && !adding()) {
            <p style="color:#475569;font-size:14px;text-align:center;padding:20px 0;">Aucun article. Cliquez sur "Ajouter" pour commencer.</p>
          }
        </div>

        <!-- Envoyer l'édition -->
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;">
          <h2 style="color:#f1f5f9;margin:0 0 4px;font-size:20px;">Envoyer l'édition</h2>
          <p style="color:#64748b;font-size:13px;margin:0 0 20px;">
            Sera envoyée aux <strong style="color:#22d3ee;">{{ stats()?.active ?? '?' }} abonnés actifs</strong>
            avec les <strong style="color:#f1f5f9;">{{ articles().length }} articles</strong> ci-dessus.
          </p>

          <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
            <div>
              <label style="display:block;color:#94a3b8;font-size:12px;font-weight:600;letter-spacing:1px;margin-bottom:6px;">NUMÉRO D'ÉDITION</label>
              <input type="number" [(ngModel)]="editionNumber"
                style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:10px 14px;color:#f1f5f9;font-size:14px;outline:none;width:100px;">
            </div>
            <button (click)="sendFromSchedule()"
              [disabled]="articles().length === 0 || sending()"
              style="margin-top:20px;background:linear-gradient(135deg,#0891b2,#0e7490);color:#fff;border:none;border-radius:10px;padding:12px 28px;font-size:14px;font-weight:700;cursor:pointer;"
              [style.opacity]="articles().length === 0 || sending() ? '0.5' : '1'">
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
  private fb = inject(FormBuilder);

  apiKeySet        = signal(false);
  keyInput         = '';
  keyError         = signal(false);
  stats            = signal<Stats | null>(null);
  articles         = signal<Article[]>([]);
  sending          = signal(false);
  sendResult       = signal<{ ok: boolean; message: string } | null>(null);
  editingPosition  = signal<number | null>(null);
  adding           = signal(false);
  editionNumber    = 1;

  articleForm = this.fb.nonNullable.group({
    position:    [1,   [Validators.required, Validators.min(1), Validators.max(6)]],
    actu_title:  ['',  Validators.required],
    actu_url:    ['',  Validators.required],
    actu_source: ['',  Validators.required],
    reflex:      ['',  Validators.required],
    image_url:   ['' as string | null],
  });

  ngOnInit() {
    const saved = sessionStorage.getItem('admin_key');
    if (saved) { this.apiKeySet.set(true); this.keyInput = saved; this.loadStats(); this.loadSchedule(); }
  }

  private headers() {
    return new HttpHeaders({ 'X-Admin-Key': this.keyInput });
  }

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
      next: data => this.articles.set(data),
    });
  }

  startAdd() {
    this.editingPosition.set(null);
    this.adding.set(true);
    const nextPos = this.articles().length + 1;
    this.articleForm.reset({ position: nextPos, actu_title: '', actu_url: '', actu_source: '', reflex: '' });
  }

  startEdit(a: Article) {
    this.adding.set(false);
    this.editingPosition.set(a.position);
    this.articleForm.setValue({ position: a.position, actu_title: a.actu_title, actu_url: a.actu_url, actu_source: a.actu_source, reflex: a.reflex, image_url: a.image_url ?? null });
  }

  cancelEdit() {
    this.editingPosition.set(null);
    this.adding.set(false);
  }

  saveArticle(oldPosition: number) {
    if (this.articleForm.invalid) return;
    const current = this.articles();
    const updated = current.map(a => a.position === oldPosition ? { ...a, ...this.articleForm.getRawValue() } : a);
    this._saveSchedule(updated);
  }

  saveNewArticle() {
    if (this.articleForm.invalid) return;
    const newArticle = this.articleForm.getRawValue() as Article;
    const updated = [...this.articles().filter(a => a.position !== newArticle.position), newArticle]
      .sort((a, b) => a.position - b.position);
    this._saveSchedule(updated);
  }

  deleteArticle(position: number) {
    const updated = this.articles()
      .filter(a => a.position !== position)
      .map((a, i) => ({ ...a, position: i + 1 }));
    this._saveSchedule(updated);
  }

  private _saveSchedule(items: Article[]) {
    this.http.put<Article[]>(`${environment.apiUrl}/newsletter/admin/schedule`, items, { headers: this.headers() }).subscribe({
      next: data => { this.articles.set(data); this.cancelEdit(); },
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
    this.articles.set([]);
  }
}
