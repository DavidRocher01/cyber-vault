export interface RadarCategory {
  label: string;
  keys: string[];
}

export const RADAR_CATEGORIES: RadarCategory[] = [
  { label: 'SSL/TLS',        keys: ['ssl', 'tls'] },
  { label: 'Headers',        keys: ['headers', 'cors', 'cookies'] },
  { label: 'Infrastructure', keys: ['ip', 'dns', 'waf'] },
  { label: 'Applicatif',     keys: ['cms', 'http_methods', 'tech'] },
  { label: 'Email & Bots',   keys: ['email', 'robots'] },
  { label: 'Avancé',         keys: ['threat_intel', 'jwt', 'open_redirect', 'clickjacking', 'directory_listing', 'takeover'] },
];

const MODULE_WEIGHTS: Record<string, number> = {
  ssl: 3, headers: 3, email: 1, cookies: 1, cors: 1.5,
  ip: 1, dns: 1, cms: 0.5, waf: 1,
  tech: 1, tls: 2, takeover: 1.5, threat_intel: 2, http_methods: 1,
  open_redirect: 2, clickjacking: 1, directory_listing: 1.5, robots: 0.5, jwt: 2,
};

export function moduleScore(status: string | null | undefined): number | null {
  switch (status) {
    case 'OK':       return 100;
    case 'WARNING':  return 50;
    case 'CRITICAL': return 0;
    default:         return null;
  }
}

export function computeScore(resultsJson: string | null): number | null {
  if (!resultsJson) return null;
  let r: Record<string, Record<string, unknown>>;
  try { r = JSON.parse(resultsJson); } catch { return null; }

  let totalWeight = 0;
  let weightedSum = 0;

  for (const [key, weight] of Object.entries(MODULE_WEIGHTS)) {
    const data = r[key];
    if (!data || Object.keys(data).length === 0) continue;
    const score = moduleScore(data['status'] as string | null);
    if (score === null) continue;
    weightedSum += score * weight;
    totalWeight += weight;
  }

  if (totalWeight === 0) return null;
  return Math.round(weightedSum / totalWeight);
}

export function getGrade(score: number): string {
  if (score >= 90) return 'A';
  if (score >= 75) return 'B';
  if (score >= 60) return 'C';
  if (score >= 40) return 'D';
  return 'F';
}

export function getScoreColor(score: number): string {
  if (score >= 90) return '#4ade80';
  if (score >= 75) return '#a3e635';
  if (score >= 60) return '#facc15';
  if (score >= 40) return '#fb923c';
  return '#f87171';
}

export function getCategoryScores(resultsJson: string | null): number[] {
  if (!resultsJson) return RADAR_CATEGORIES.map(() => 0);
  let r: Record<string, Record<string, unknown>>;
  try { r = JSON.parse(resultsJson); } catch { return RADAR_CATEGORIES.map(() => 0); }

  return RADAR_CATEGORIES.map(cat => {
    const scores = cat.keys
      .map(k => moduleScore((r[k]?.['status'] ?? null) as string | null))
      .filter((s): s is number => s !== null);
    if (scores.length === 0) return 0;
    return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  });
}
