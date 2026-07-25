/**
 * Source unique des libellés et classes CSS des actions/priorités RSSI
 * (côté consultant : client-detail + son sous-composant actions-table).
 *
 * Ces deux composants portaient une copie strictement identique de ces switch ;
 * elles sont factorisées ici. Le portail client (client-portal) garde
 * volontairement son propre style plus léger (badges texte, libellés « À faire »
 * / « Réalisée ») adapté à l'audience client — ne pas le rabattre ici.
 */

export function priorityClass(p: string): string {
  switch (p) {
    case 'critical':
      return 'text-red-400 bg-red-500/10 border-red-600/30';
    case 'high':
      return 'text-orange-400 bg-orange-500/10 border-orange-600/30';
    case 'medium':
      return 'text-yellow-400 bg-yellow-500/10 border-yellow-600/30';
    default:
      return 'text-gray-400 bg-gray-700/20 border-gray-600/30';
  }
}

export function actionStatusClass(s: string): string {
  switch (s) {
    case 'done':
      return 'text-green-400 bg-green-500/10 border-green-600/30';
    case 'in_progress':
      return 'text-blue-400 bg-blue-500/10 border-blue-600/30';
    case 'cancelled':
      return 'text-gray-500 bg-gray-700/20 border-gray-600/30';
    case 'postponed':
      return 'text-yellow-400 bg-yellow-500/10 border-yellow-600/30';
    default:
      return 'text-white bg-gray-700/30 border-gray-600/40';
  }
}

const ACTION_STATUS_LABELS: Record<string, string> = {
  open: 'Ouverte',
  in_progress: 'En cours',
  done: 'Terminée',
  cancelled: 'Annulée',
  postponed: 'Reportée',
};

export function actionStatusLabel(s: string): string {
  return ACTION_STATUS_LABELS[s] ?? s;
}
