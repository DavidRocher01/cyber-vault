/**
 * Helpers de présentation (libellés + classes CSS) de la fiche client RSSI.
 * Fonctions pures extraites du god-component client-detail pour l'alléger et
 * les rendre testables isolément (le découpage complet par onglet est différé).
 */

export function docTypeLabel(t: string): string {
  const map: Record<string, string> = {
    compte_rendu: 'Compte-rendu',
    rapport: 'Rapport',
    recommandation: 'Recommandation',
    contrat: 'Contrat',
    autre: 'Autre',
  };
  return map[t] ?? t;
}

export function docTypeClass(t: string): string {
  switch (t) {
    case 'compte_rendu':
      return 'text-blue-300 bg-blue-500/10 border-blue-600/30';
    case 'rapport':
      return 'text-cyan-300 bg-cyan-500/10 border-cyan-600/30';
    case 'recommandation':
      return 'text-purple-300 bg-purple-500/10 border-purple-600/30';
    case 'contrat':
      return 'text-amber-300 bg-amber-500/10 border-amber-600/30';
    default:
      return 'text-gray-400 bg-gray-700/20 border-gray-600/30';
  }
}

export function formulaLabel(f: string | null): string {
  const map: Record<string, string> = {
    essentiel: 'Essentiel',
    premium: 'Premium',
    excellence: 'Excellence',
  };
  return f ? (map[f] ?? f) : '—';
}

export function formulaClass(f: string | null): string {
  switch (f) {
    case 'essentiel':
      return 'text-blue-300 bg-blue-500/10 border-blue-600/30';
    case 'premium':
      return 'text-purple-300 bg-purple-500/10 border-purple-600/30';
    case 'excellence':
      return 'text-amber-300 bg-amber-500/10 border-amber-600/30';
    default:
      return 'text-gray-400 bg-gray-700/20 border-gray-600/30';
  }
}

export function clientStatusClass(status: string): string {
  switch (status) {
    case 'active':
      return 'text-green-300';
    case 'inactive':
      return 'text-yellow-300';
    case 'churned':
      return 'text-red-300';
    default:
      return 'text-gray-400';
  }
}

export function visitStatusClass(s: string): string {
  switch (s) {
    case 'completed':
      return 'text-green-400';
    case 'cancelled':
      return 'text-red-400';
    case 'postponed':
      return 'text-yellow-400';
    default:
      return 'text-blue-300';
  }
}

export function visitStatusLabel(s: string): string {
  const map: Record<string, string> = {
    planned: 'Planifiée',
    completed: 'Complétée',
    cancelled: 'Annulée',
    postponed: 'Reportée',
  };
  return map[s] ?? s;
}

export function visitTypeLabel(t: string): string {
  const map: Record<string, string> = {
    monthly: 'Mensuelle',
    quarterly: 'Trimestrielle',
    annual: 'Annuelle',
    urgent: 'Urgente',
  };
  return map[t] ?? t;
}

export function visitLocationLabel(l: string): string {
  return l === 'onsite' ? 'Sur site' : 'À distance';
}

export function activityLabel(type: string): string {
  const map: Record<string, string> = {
    view_client: 'Consultation fiche client',
    view_sites: 'Consultation des sites',
    view_scans: 'Consultation des scans',
    view_findings: 'Consultation des findings',
    generate_report: 'Génération de rapport',
    send_deliverable: "Envoi d'un livrable",
    create_action: "Création d'une action",
    update_action: "Mise à jour d'une action",
    create_visit: "Planification d'une visite",
    update_visit: "Mise à jour d'une visite",
  };
  return map[type] ?? type;
}

export function scanStatusClass(s: 'OK' | 'WARNING' | 'CRITICAL' | null): string {
  switch (s) {
    case 'OK':
      return 'text-green-400 bg-green-500/10 border-green-600/30';
    case 'WARNING':
      return 'text-yellow-400 bg-yellow-500/10 border-yellow-600/30';
    case 'CRITICAL':
      return 'text-red-400 bg-red-500/10 border-red-600/30';
    default:
      return 'text-gray-500 bg-gray-700/20 border-gray-600/30';
  }
}

export function scanStatusLabel(s: 'OK' | 'WARNING' | 'CRITICAL' | null): string {
  if (!s) return 'Aucun scan';
  return s;
}
