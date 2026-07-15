import { Component, inject, signal, OnInit } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { Title } from '@angular/platform-browser';
import { forkJoin } from 'rxjs';

import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { ScoreGaugeComponent } from '../../../shared/score-gauge/score-gauge.component';
import {
  ClientPortalService,
  PortalMe,
  PortalAction,
  PortalVisit,
  PortalDeliverable,
} from '../services/client-portal.service';

@Component({
  standalone: true,
  selector: 'app-client-portal',
  imports: [MatIconModule, NavButtonsComponent, ScoreGaugeComponent],
  templateUrl: './client-portal.component.html',
})
export class ClientPortalComponent implements OnInit {
  private service = inject(ClientPortalService);
  private title = inject(Title);

  me = signal<PortalMe | null>(null);
  actions = signal<PortalAction[]>([]);
  visits = signal<PortalVisit[]>([]);
  deliverables = signal<PortalDeliverable[]>([]);
  loading = signal(true);
  error = signal(false);
  reportLoading = signal(false);

  ngOnInit() {
    this.title.setTitle('Mon espace sécurité | Rocher Cybersécurité');
    forkJoin({
      me: this.service.getMe(),
      actions: this.service.getActions(),
      visits: this.service.getVisits(),
      deliverables: this.service.getDeliverables(),
    }).subscribe({
      next: ({ me, actions, visits, deliverables }) => {
        this.me.set(me);
        this.actions.set(actions);
        this.visits.set(visits);
        this.deliverables.set(deliverables);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }

  openDeliverable(id: number) {
    this.service.getDeliverableUrl(id).subscribe({
      next: ({ url }) => window.open(url, '_blank'),
    });
  }

  downloadReport() {
    this.reportLoading.set(true);
    this.service.downloadReport().subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'rapport_securite.pdf';
        a.click();
        URL.revokeObjectURL(url);
        this.reportLoading.set(false);
      },
      error: () => this.reportLoading.set(false),
    });
  }

  // ── Libellés / couleurs ─────────────────────────────────────────────────────

  private static PRIORITY: Record<string, [string, string]> = {
    critical: ['Critique', 'bg-red-500/15 text-red-400 border-red-700/40'],
    high: ['Haute', 'bg-orange-500/15 text-orange-400 border-orange-700/40'],
    medium: ['Moyenne', 'bg-yellow-500/15 text-yellow-400 border-yellow-700/40'],
    low: ['Basse', 'bg-gray-500/15 text-gray-400 border-gray-600/40'],
  };
  private static ACTION_STATUS: Record<string, [string, string]> = {
    open: ['À faire', 'text-gray-400'],
    in_progress: ['En cours', 'text-amber-400'],
    done: ['Terminée', 'text-green-400'],
    cancelled: ['Annulée', 'text-gray-500'],
    postponed: ['Reportée', 'text-gray-400'],
  };
  private static VISIT_TYPE: Record<string, string> = {
    monthly: 'Point mensuel',
    quarterly: 'Comité trimestriel',
    annual: 'Revue annuelle',
    urgent: 'Intervention urgente',
  };
  private static VISIT_STATUS: Record<string, [string, string]> = {
    planned: ['Planifiée', 'text-cyan-400'],
    done: ['Réalisée', 'text-green-400'],
    cancelled: ['Annulée', 'text-gray-500'],
  };
  private static DOC_TYPE: Record<string, string> = {
    compte_rendu: 'Compte rendu',
    rapport: 'Rapport',
    recommandation: 'Recommandation',
    contrat: 'Contrat',
    autre: 'Document',
  };
  private static FORMULA: Record<string, string> = {
    essentiel: 'Essentiel',
    premium: 'Premium',
    excellence: 'Excellence',
  };

  priorityLabel(p: string): string {
    return ClientPortalComponent.PRIORITY[p]?.[0] ?? p;
  }
  priorityClass(p: string): string {
    return (
      ClientPortalComponent.PRIORITY[p]?.[1] ?? 'bg-gray-500/15 text-gray-400 border-gray-600/40'
    );
  }
  actionStatusLabel(s: string): string {
    return ClientPortalComponent.ACTION_STATUS[s]?.[0] ?? s;
  }
  actionStatusClass(s: string): string {
    return ClientPortalComponent.ACTION_STATUS[s]?.[1] ?? 'text-gray-400';
  }
  visitTypeLabel(t: string): string {
    return ClientPortalComponent.VISIT_TYPE[t] ?? t;
  }
  visitStatusLabel(s: string): string {
    return ClientPortalComponent.VISIT_STATUS[s]?.[0] ?? s;
  }
  visitStatusClass(s: string): string {
    return ClientPortalComponent.VISIT_STATUS[s]?.[1] ?? 'text-gray-400';
  }
  docTypeLabel(d: string): string {
    return ClientPortalComponent.DOC_TYPE[d] ?? d;
  }
  formulaLabel(f: string | null): string {
    return f ? (ClientPortalComponent.FORMULA[f] ?? f) : '—';
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    const date = new Date(d);
    return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });
  }

  isDone(a: PortalAction): boolean {
    return a.status === 'done';
  }
}
