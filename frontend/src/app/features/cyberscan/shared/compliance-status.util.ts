/**
 * Helpers de présentation partagés des checklists de conformité
 * (NIS2 + ISO 27001), qui portaient une copie identique de ces fonctions.
 * Statuts : compliant | partial | non_compliant | na.
 */

export function complianceStatusLabel(s: string): string {
  const map: Record<string, string> = {
    compliant: 'Conforme',
    partial: 'Partiel',
    non_compliant: 'Non conforme',
    na: 'N/A',
  };
  return map[s] ?? s;
}

export function complianceStatusIcon(s: string): string {
  const map: Record<string, string> = {
    compliant: 'check_circle',
    partial: 'pending',
    non_compliant: 'cancel',
    na: 'remove_circle_outline',
  };
  return map[s] ?? 'help_outline';
}

export function complianceStatusClass(s: string): string {
  const map: Record<string, string> = {
    compliant: 'text-green-400 bg-green-400/10 border-green-700',
    partial: 'text-yellow-400 bg-yellow-400/10 border-yellow-700',
    non_compliant: 'text-red-400 bg-red-400/10 border-red-700',
    na: 'text-gray-400 bg-gray-700/30 border-gray-600',
  };
  return map[s] ?? 'text-gray-400 bg-gray-700/30 border-gray-600';
}

export function complianceStatusColor(s: string): string {
  const map: Record<string, string> = {
    compliant: '#4ade80',
    partial: '#facc15',
    non_compliant: '#f87171',
    na: '#6b7280',
  };
  return map[s] ?? '#6b7280';
}

export function complianceScoreColor(n: number): string {
  if (n >= 80) return '#4ade80';
  if (n >= 50) return '#facc15';
  return '#f87171';
}

export function complianceScoreLabel(n: number): string {
  if (n >= 80) return 'Conforme';
  if (n >= 50) return 'En cours';
  return 'Non conforme';
}
