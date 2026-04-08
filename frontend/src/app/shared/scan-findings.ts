export interface Finding {
  key: string;
  label: string;
  icon: string;
  minTier: number;
  skipped: boolean;
  status: 'OK' | 'WARNING' | 'CRITICAL' | null;
  summary: { label: string; value: string }[];
}

export const MODULE_META: { key: string; label: string; icon: string; minTier: number }[] = [
  { key: 'ssl',               label: 'Certificat SSL/TLS',     icon: 'https',         minTier: 1 },
  { key: 'headers',           label: 'Headers HTTP',            icon: 'security',      minTier: 1 },
  { key: 'email',             label: 'Sécurité Email',          icon: 'email',         minTier: 1 },
  { key: 'cookies',           label: 'Cookies',                 icon: 'cookie',        minTier: 1 },
  { key: 'cors',              label: 'CORS',                    icon: 'share',         minTier: 1 },
  { key: 'ip',                label: 'Réputation IP',           icon: 'gps_fixed',     minTier: 1 },
  { key: 'dns',               label: 'DNS / Sous-domaines',     icon: 'dns',           minTier: 1 },
  { key: 'cms',               label: 'Détection CMS',           icon: 'web',           minTier: 1 },
  { key: 'waf',               label: 'Pare-feu (WAF)',          icon: 'shield',        minTier: 1 },
  { key: 'tech',              label: 'Empreinte Tech.',         icon: 'code',          minTier: 3 },
  { key: 'tls',               label: 'Audit TLS',               icon: 'lock',          minTier: 3 },
  { key: 'takeover',          label: 'Subdomain Takeover',      icon: 'warning',       minTier: 3 },
  { key: 'threat_intel',      label: 'Threat Intelligence',     icon: 'bug_report',    minTier: 3 },
  { key: 'http_methods',      label: 'Méthodes HTTP',           icon: 'http',          minTier: 3 },
  { key: 'open_redirect',     label: 'Redirections ouvertes',   icon: 'open_in_new',   minTier: 4 },
  { key: 'clickjacking',      label: 'Clickjacking',            icon: 'layers',        minTier: 4 },
  { key: 'directory_listing', label: 'Listing répertoire',      icon: 'folder_open',   minTier: 4 },
  { key: 'robots',            label: 'Robots / Sitemap',        icon: 'smart_toy',     minTier: 4 },
  { key: 'jwt',               label: 'Tokens JWT',              icon: 'vpn_key',       minTier: 4 },
];

export function extractSummary(key: string, d: Record<string, unknown>): { label: string; value: string }[] {
  if (!d || Object.keys(d).length === 0) return [];

  switch (key) {
    case 'ssl':
      return [
        d['issuer']    ? { label: 'Émetteur',     value: String(d['issuer']) }                     : null,
        d['days_left'] != null ? { label: 'Expire dans', value: `${d['days_left']} jours` }        : null,
        d['protocols'] ? { label: 'Protocoles',   value: (d['protocols'] as string[]).join(', ') } : null,
      ].filter(Boolean) as { label: string; value: string }[];

    case 'headers': {
      const missing = d['missing_headers'] as string[] | undefined;
      return missing?.length
        ? [{ label: 'Headers manquants', value: missing.slice(0, 4).join(', ') }]
        : [{ label: 'Headers manquants', value: 'Aucun' }];
    }

    case 'email': {
      const items = [];
      if (d['spf']   != null) items.push({ label: 'SPF',   value: d['spf']   ? 'Présent' : 'Absent' });
      if (d['dkim']  != null) items.push({ label: 'DKIM',  value: d['dkim']  ? 'Présent' : 'Absent' });
      if (d['dmarc'] != null) items.push({ label: 'DMARC', value: d['dmarc'] ? 'Présent' : 'Absent' });
      return items;
    }

    case 'cookies': {
      const issues = d['issues'] as string[] | undefined;
      return issues?.length
        ? [{ label: 'Problèmes', value: issues.slice(0, 3).join(', ') }]
        : [{ label: 'Cookies', value: 'Configuration correcte' }];
    }

    case 'cors':
      return d['allow_origin']
        ? [{ label: 'Access-Control-Allow-Origin', value: String(d['allow_origin']).slice(0, 40) }]
        : [{ label: 'CORS', value: 'En-tête absent' }];

    case 'ip':
      return [
        d['ip']          ? { label: 'IP',        value: String(d['ip']) }      : null,
        d['country']     ? { label: 'Pays',      value: String(d['country']) } : null,
        d['blacklisted'] != null ? { label: 'Blacklist', value: d['blacklisted'] ? 'Oui' : 'Non' } : null,
      ].filter(Boolean) as { label: string; value: string }[];

    case 'dns': {
      const found = d['found'] as { subdomain: string }[] | undefined;
      return found?.length
        ? [{ label: 'Sous-domaines trouvés', value: `${found.length}` }]
        : [{ label: 'Sous-domaines', value: 'Aucun trouvé' }];
    }

    case 'cms':
      return d['cms']
        ? [{ label: 'CMS détecté', value: String(d['cms']) }]
        : [{ label: 'CMS', value: 'Non détecté' }];

    case 'waf':
      return d['waf']
        ? [{ label: 'WAF détecté', value: String(d['waf']) }]
        : [{ label: 'WAF', value: 'Non détecté' }];

    case 'tech': {
      const techs = d['technologies'] as string[] | undefined;
      return techs?.length
        ? [{ label: 'Technologies', value: techs.slice(0, 5).join(', ') }]
        : [];
    }

    case 'tls':
      return [
        d['grade']    ? { label: 'Grade SSL Labs', value: String(d['grade']) }    : null,
        d['protocol'] ? { label: 'Protocole min',  value: String(d['protocol']) } : null,
      ].filter(Boolean) as { label: string; value: string }[];

    case 'threat_intel': {
      const vulns = d['vulns']      as string[] | undefined;
      const ports  = d['open_ports'] as number[] | undefined;
      return [
        ports?.length ? { label: 'Ports ouverts', value: ports.slice(0, 6).join(', ') } : null,
        vulns?.length ? { label: 'CVE détectées', value: `${vulns.length}` }             : null,
      ].filter(Boolean) as { label: string; value: string }[];
    }

    case 'http_methods': {
      const dangerous = d['dangerous_methods'] as string[] | undefined;
      return dangerous?.length
        ? [{ label: 'Méthodes dangereuses', value: dangerous.join(', ') }]
        : [{ label: 'Méthodes', value: 'Aucune dangereuse' }];
    }

    case 'jwt': {
      const issues = d['issues'] as string[] | undefined;
      return issues?.length
        ? [{ label: 'Problèmes JWT', value: issues.slice(0, 3).join(', ') }]
        : [{ label: 'JWT', value: 'Aucun token détecté' }];
    }

    default:
      return Object.entries(d)
        .filter(([k, v]) => k !== 'status' && (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean'))
        .slice(0, 3)
        .map(([k, v]) => ({ label: k.replace(/_/g, ' '), value: String(v) }));
  }
}

export function getFindings(resultsJson: string | null): Finding[] {
  if (!resultsJson) return [];
  let r: Record<string, Record<string, unknown>>;
  try { r = JSON.parse(resultsJson); } catch { return []; }

  const tier = (r['_meta']?.['tier'] as number) ?? 2;

  return MODULE_META.map(m => {
    const data = r[m.key] ?? {};
    const skipped = tier < m.minTier || Object.keys(data).length === 0;
    return {
      ...m,
      skipped,
      status: skipped ? null : (data['status'] as 'OK' | 'WARNING' | 'CRITICAL' | null ?? null),
      summary: skipped ? [] : extractSummary(m.key, data),
    };
  });
}
