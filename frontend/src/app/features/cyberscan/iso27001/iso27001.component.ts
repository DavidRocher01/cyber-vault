import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Title, Meta } from '@angular/platform-browser';

import { ComplianceApiService } from '../services/compliance-api.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import {
  complianceStatusLabel,
  complianceStatusIcon,
  complianceStatusClass,
  complianceStatusColor,
  complianceScoreColor,
  complianceScoreLabel,
} from '../shared/compliance-status.util';

export type Iso27001Status = 'compliant' | 'partial' | 'non_compliant' | 'na';

export interface Iso27001Item {
  id: string;
  label: string;
  desc: string;
}

export interface Iso27001Category {
  id: string;
  label: string;
  icon: string;
  items: Iso27001Item[];
}

@Component({
  standalone: true,
  selector: 'app-iso27001',
  imports: [
    RouterLink,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    NavButtonsComponent,
  ],
  templateUrl: './iso27001.component.html',
})
export class Iso27001Component implements OnInit {
  private complianceApi = inject(ComplianceApiService);
  private snack = inject(MatSnackBar);
  private titleService = inject(Title);
  private meta = inject(Meta);

  loading = signal(true);
  saving = signal(false);
  exporting = signal(false);

  categories = signal<Iso27001Category[]>([]);
  items = signal<Record<string, Iso27001Status>>({});
  score = signal(0);
  updatedAt = signal<string | null>(null);

  private readonly CYCLE: Iso27001Status[] = ['non_compliant', 'partial', 'compliant', 'na'];
  readonly STATUS_LIST: Iso27001Status[] = ['compliant', 'partial', 'non_compliant', 'na'];

  ngOnInit() {
    this.titleService.setTitle('Conformité ISO 27001:2022 — Rocher Cybersécurité');
    this.meta.updateTag({
      name: 'description',
      content:
        'Évaluez votre niveau de conformité à la norme ISO/IEC 27001:2022 avec Rocher Cybersécurité.',
    });
    this.complianceApi.getIso27001Assessment().subscribe({
      next: data => {
        // Narrowing au bord de l'API : le backend renvoie des chaînes/objets
        // generiques dont les valeurs sont garanties valides pour ces types.
        this.categories.set((data.categories ?? []) as Iso27001Category[]);
        this.items.set((data.items ?? {}) as Record<string, Iso27001Status>);
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

  getStatus(itemId: string): Iso27001Status {
    return this.items()[itemId] ?? 'non_compliant';
  }

  toggle(itemId: string) {
    const current = this.getStatus(itemId);
    const idx = this.CYCLE.indexOf(current);
    const next = this.CYCLE[(idx + 1) % this.CYCLE.length];
    this.items.update(m => ({ ...m, [itemId]: next }));
    this.recalcScore();
  }

  setStatus(itemId: string, status: Iso27001Status) {
    this.items.update(m => ({ ...m, [itemId]: status }));
    this.recalcScore();
  }

  recalcScore() {
    const allIds = this.categories().flatMap(cat => cat.items.map(i => i.id));
    const vals = allIds.map(id => this.getStatus(id)).filter(v => v !== 'na');
    if (!vals.length) {
      this.score.set(0);
      return;
    }
    const pts = vals.reduce((s, v) => s + (v === 'compliant' ? 2 : v === 'partial' ? 1 : 0), 0);
    this.score.set(Math.round((pts / (vals.length * 2)) * 100));
  }

  resetAll() {
    this.items.set({});
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
    this.complianceApi.saveIso27001Assessment(this._fullItems).subscribe({
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
    this.complianceApi.saveIso27001Assessment(this._fullItems).subscribe({
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
    this.complianceApi.downloadIso27001PdfBlob().subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'cyberscan_iso27001_conformite.pdf';
        a.click();
        URL.revokeObjectURL(url);
        this.exporting.set(false);
      },
      error: () => {
        this.exporting.set(false);
        this.snack.open("Erreur lors de l'export PDF", 'Fermer', { duration: 4000 });
      },
    });
  }

  statusLabel(s: string): string {
    return complianceStatusLabel(s);
  }

  statusIcon(s: string): string {
    return complianceStatusIcon(s);
  }

  statusClass(s: string): string {
    return complianceStatusClass(s);
  }

  statusColor(s: string): string {
    return complianceStatusColor(s);
  }

  scoreColor(n: number): string {
    return complianceScoreColor(n);
  }

  scoreLabel(n: number): string {
    return complianceScoreLabel(n);
  }

  catCompliance(cat: Iso27001Category): {
    compliant: number;
    partial: number;
    nc: number;
    total: number;
  } {
    return {
      compliant: cat.items.filter(i => this.getStatus(i.id) === 'compliant').length,
      partial: cat.items.filter(i => this.getStatus(i.id) === 'partial').length,
      nc: cat.items.filter(i => this.getStatus(i.id) === 'non_compliant').length,
      total: cat.items.length,
    };
  }

  catScore(cat: Iso27001Category): number {
    const scorable = cat.items.filter(i => this.getStatus(i.id) !== 'na');
    if (!scorable.length) return 0;
    const pts = scorable.reduce((s, i) => {
      const v = this.getStatus(i.id);
      return s + (v === 'compliant' ? 2 : v === 'partial' ? 1 : 0);
    }, 0);
    return Math.round((pts / (scorable.length * 2)) * 100);
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  readonly totalItems = computed(() => this.categories().reduce((s, c) => s + c.items.length, 0));

  private readonly allItemIds = computed(() =>
    this.categories().flatMap(cat => cat.items.map(i => i.id))
  );

  readonly compliantCount = computed(
    () => this.allItemIds().filter(id => this.getStatus(id) === 'compliant').length
  );
  readonly partialCount = computed(
    () => this.allItemIds().filter(id => this.getStatus(id) === 'partial').length
  );
  readonly ncCount = computed(
    () => this.allItemIds().filter(id => this.getStatus(id) === 'non_compliant').length
  );
  readonly naCount = computed(
    () => this.allItemIds().filter(id => this.getStatus(id) === 'na').length
  );
}
