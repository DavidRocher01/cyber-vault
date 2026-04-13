import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { CyberscanService } from '../services/cyberscan.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

export type Nis2Status = 'compliant' | 'partial' | 'non_compliant' | 'na';

export interface Nis2Item {
  id: string;
  label: string;
  desc: string;
}

export interface Nis2Category {
  id: string;
  label: string;
  icon: string;
  items: Nis2Item[];
}

@Component({
  selector: 'app-nis2',
  standalone: true,
  imports: [
    CommonModule, RouterLink,
    MatIconModule, MatProgressSpinnerModule, MatSnackBarModule, MatTooltipModule,
    NavButtonsComponent,
  ],
  templateUrl: './nis2.component.html',
})
export class Nis2Component implements OnInit {
  private cyberscan = inject(CyberscanService);
  private snack = inject(MatSnackBar);

  loading = signal(true);
  saving = signal(false);
  exporting = signal(false);

  categories = signal<Nis2Category[]>([]);
  items = signal<Record<string, Nis2Status>>({});
  score = signal(0);
  updatedAt = signal<string | null>(null);

  // Status cycle: non_compliant → partial → compliant → na → non_compliant
  private readonly CYCLE: Nis2Status[] = ['non_compliant', 'partial', 'compliant', 'na'];
  readonly STATUS_LIST: Nis2Status[] = ['compliant', 'partial', 'non_compliant', 'na'];

  ngOnInit() {
    this.cyberscan.getNis2Assessment().subscribe({
      next: data => {
        this.categories.set(data.categories ?? []);
        this.items.set(data.items ?? {});
        this.score.set(data.score ?? 0);
        this.updatedAt.set(data.updated_at ?? null);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snack.open('Erreur lors du chargement', 'Fermer', { duration: 4000 });
      },
    });
  }

  getStatus(itemId: string): Nis2Status {
    return this.items()[itemId] ?? 'non_compliant';
  }

  toggle(itemId: string) {
    const current = this.getStatus(itemId);
    const idx = this.CYCLE.indexOf(current);
    const next = this.CYCLE[(idx + 1) % this.CYCLE.length];
    this.items.update(m => ({ ...m, [itemId]: next }));
    this.recalcScore();
  }

  setStatus(itemId: string, status: Nis2Status) {
    this.items.update(m => ({ ...m, [itemId]: status }));
    this.recalcScore();
  }

  recalcScore() {
    // Utiliser TOUS les items des catégories comme dénominateur,
    // pas seulement ceux explicitement renseignés dans le map.
    // Les items non renseignés ont getStatus() = 'non_compliant' = 0 pts.
    const allIds = this.categories().flatMap(cat => cat.items.map(i => i.id));
    const vals = allIds.map(id => this.getStatus(id)).filter(v => v !== 'na');
    if (!vals.length) { this.score.set(0); return; }
    const pts = vals.reduce((s, v) => s + (v === 'compliant' ? 2 : v === 'partial' ? 1 : 0), 0);
    this.score.set(Math.round(pts / (vals.length * 2) * 100));
  }

  resetAll() {
    const allIds = this.categories().flatMap(cat => cat.items.map(i => i.id));
    const reset: Record<string, Nis2Status> = {};
    for (const id of allIds) reset[id] = 'na';
    this.items.set(reset);
    this.recalcScore();
  }

  private get _fullItems(): Record<string, string> {
    const allIds = this.categories().flatMap(cat => cat.items.map(i => i.id));
    const full: Record<string, string> = {};
    for (const id of allIds) full[id] = this.getStatus(id);
    return full;
  }

  save() {
    this.saving.set(true);
    this.cyberscan.saveNis2Assessment(this._fullItems).subscribe({
      next: data => {
        this.score.set(data.score);
        this.updatedAt.set(data.updated_at);
        this.saving.set(false);
        this.snack.open('Évaluation sauvegardée', 'OK', { duration: 3000 });
      },
      error: () => {
        this.saving.set(false);
        this.snack.open('Erreur lors de la sauvegarde', 'Fermer', { duration: 4000 });
      },
    });
  }

  exportPdf() {
    this.exporting.set(true);
    // Sauvegarde automatique avant export pour garantir la cohérence PDF/app
    this.cyberscan.saveNis2Assessment(this._fullItems).subscribe({
      next: data => {
        this.score.set(data.score);
        this.updatedAt.set(data.updated_at);
        this._downloadPdf();
      },
      error: () => {
        this.exporting.set(false);
        this.snack.open('Erreur lors de la sauvegarde avant export', 'Fermer', { duration: 4000 });
      },
    });
  }

  private _downloadPdf() {
    this.cyberscan.downloadNis2PdfBlob().subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'cyberscan_nis2_conformite.pdf';
        a.click();
        URL.revokeObjectURL(url);
        this.exporting.set(false);
      },
      error: () => {
        this.exporting.set(false);
        this.snack.open('Erreur lors de l\'export PDF', 'Fermer', { duration: 4000 });
      },
    });
  }

  // ── Helpers ────────────────────────────────────────────────────────────

  statusLabel(s: string): string {
    const map: Record<string, string> = {
      compliant: 'Conforme', partial: 'Partiel',
      non_compliant: 'Non conforme', na: 'N/A',
    };
    return map[s] ?? s;
  }

  statusIcon(s: string): string {
    const map: Record<string, string> = { compliant: 'check_circle', partial: 'pending', non_compliant: 'cancel', na: 'remove_circle_outline' };
    return map[s] ?? 'help_outline';
  }

  statusClass(s: string): string {
    const map: Record<string, string> = {
      compliant:     'text-green-400 bg-green-400/10 border-green-700',
      partial:       'text-yellow-400 bg-yellow-400/10 border-yellow-700',
      non_compliant: 'text-red-400 bg-red-400/10 border-red-700',
      na:            'text-gray-400 bg-gray-700/30 border-gray-600',
    };
    return map[s] ?? 'text-gray-400 bg-gray-700/30 border-gray-600';
  }

  statusColor(s: string): string {
    const map: Record<string, string> = { compliant: '#4ade80', partial: '#facc15', non_compliant: '#f87171', na: '#6b7280' };
    return map[s] ?? '#6b7280';
  }

  scoreColor(n: number): string {
    if (n >= 80) return '#4ade80';
    if (n >= 50) return '#facc15';
    return '#f87171';
  }

  scoreLabel(n: number): string {
    if (n >= 80) return 'Conforme';
    if (n >= 50) return 'En cours';
    return 'Non conforme';
  }

  catCompliance(cat: Nis2Category): { compliant: number; partial: number; nc: number; total: number } {
    const its = cat.items;
    return {
      compliant: its.filter(i => this.getStatus(i.id) === 'compliant').length,
      partial:   its.filter(i => this.getStatus(i.id) === 'partial').length,
      nc:        its.filter(i => this.getStatus(i.id) === 'non_compliant').length,
      total:     its.length,
    };
  }

  catScore(cat: Nis2Category): number {
    const scorable = cat.items.filter(i => this.getStatus(i.id) !== 'na');
    if (!scorable.length) return 0;
    const pts = scorable.reduce((s, i) => {
      const v = this.getStatus(i.id);
      return s + (v === 'compliant' ? 2 : v === 'partial' ? 1 : 0);
    }, 0);
    return Math.round(pts / (scorable.length * 2) * 100);
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  get totalItems(): number {
    return this.categories().reduce((s, c) => s + c.items.length, 0);
  }
  private get allItemIds(): string[] {
    return this.categories().flatMap(cat => cat.items.map(i => i.id));
  }
  get compliantCount(): number {
    return this.allItemIds.filter(id => this.getStatus(id) === 'compliant').length;
  }
  get partialCount(): number {
    return this.allItemIds.filter(id => this.getStatus(id) === 'partial').length;
  }
  get ncCount(): number {
    return this.allItemIds.filter(id => this.getStatus(id) === 'non_compliant').length;
  }
}
