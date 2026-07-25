/**
 * Formatage de dates centralisé (locale fr-FR) — remplace les ~28 méthodes
 * `formatDate()` réimplémentées dans les composants, qui divergeaient sur une
 * dizaine de variantes. Trois presets couvrent tous les besoins réels :
 *
 *   - 'date'     → « 25 juil. 2026 »          (date seule, mois court)
 *   - 'datetime' → « 25 juil. 2026, 14:30 »   (date + heure)
 *   - 'long'     → « 25 juillet 2026 »         (mois en toutes lettres)
 *
 * Une valeur absente ou invalide rend le tiret cadratin « — » (convention UI).
 */
export type DateFormat = 'date' | 'datetime' | 'long';

const PRESETS: Record<DateFormat, Intl.DateTimeFormatOptions> = {
  date: { day: '2-digit', month: 'short', year: 'numeric' },
  datetime: {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  },
  long: { day: 'numeric', month: 'long', year: 'numeric' },
};

export function formatFrDate(
  value: string | number | Date | null | undefined,
  format: DateFormat = 'date'
): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('fr-FR', PRESETS[format]);
}
