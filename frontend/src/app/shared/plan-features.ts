/**
 * Traduit un intervalle de scan (en jours) en une formule lisible par un non-technicien.
 * Utilisé sur les cartes de tarifs (landing + onboarding) pour éviter le "Scan tous les 0 jours".
 */
export function formatScanFrequency(days: number): string {
  if (!days || days <= 0) return 'Scan à la demande';
  if (days === 1) return 'Surveillance quotidienne';
  if (days === 7) return 'Surveillance hebdomadaire';
  if (days === 30 || days === 31) return 'Surveillance mensuelle';
  if (days % 7 === 0) return `Surveillance toutes les ${days / 7} semaines`;
  return `Analyse tous les ${days} jours`;
}
