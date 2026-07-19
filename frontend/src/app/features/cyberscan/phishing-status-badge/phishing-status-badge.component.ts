import { Component, Input } from '@angular/core';

/**
 * Source unique des libellés/couleurs de statut d'une campagne de phishing.
 * Aligné sur l'enum backend `CampaignStatus`. Auparavant dupliqué (et divergent)
 * dans les composants liste / détail / édition.
 */
const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  pending_verification: 'Vérification domaine',
  ready: 'Prête',
  scheduled: 'Planifiée',
  sending: 'Envoi en cours',
  active: 'En cours',
  completed: 'Terminée',
  cancelled: 'Annulée',
};

export function phishingStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function phishingStatusColor(status: string): string {
  switch (status) {
    case 'active':
    case 'sending':
      return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
    case 'completed':
      return 'text-green-400 bg-green-500/10 border-green-500/30';
    case 'draft':
      return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
    case 'ready':
      return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
    case 'scheduled':
      return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
    case 'cancelled':
      return 'text-red-400 bg-red-500/10 border-red-500/30';
    default:
      return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
  }
}

@Component({
  standalone: true,
  selector: 'app-phishing-status-badge',
  template: `<span
    class="text-[0.7rem] font-semibold px-2 py-0.5 rounded-full border"
    [class]="color"
    >{{ label }}</span
  >`,
})
export class PhishingStatusBadgeComponent {
  @Input({ required: true }) status!: string;

  get label(): string {
    return phishingStatusLabel(this.status);
  }

  get color(): string {
    return phishingStatusColor(this.status);
  }
}
