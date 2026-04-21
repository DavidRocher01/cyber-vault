export interface Finding {
  key: string;
  label: string;
  icon: string;
  minTier: number;
  skipped: boolean;
  status: 'OK' | 'WARNING' | 'CRITICAL' | null;
  summary: { label: string; value: string }[];
  explanation: string;
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
        d['days_remaining'] != null ? { label: 'Expire dans', value: `${d['days_remaining']} jours` } : null,
        d['protocol']  ? { label: 'Protocole',    value: String(d['protocol']) }                   : null,
        d['valid']     != null ? { label: 'Valide',       value: d['valid'] ? 'Oui' : 'Non' }      : null,
      ].filter(Boolean) as { label: string; value: string }[];

    case 'headers': {
      const missing = d['headers_missing'] as string[] | undefined;
      return missing?.length
        ? [{ label: 'Headers manquants', value: missing.slice(0, 4).join(', ') }]
        : [{ label: 'Headers manquants', value: 'Aucun' }];
    }

    case 'email': {
      const spf   = d['spf']   as { found?: boolean } | null | undefined;
      const dkim  = d['dkim']  as { found?: boolean } | null | undefined;
      const dmarc = d['dmarc'] as { found?: boolean } | null | undefined;
      const items = [];
      if (spf   != null) items.push({ label: 'SPF',   value: spf.found   ? 'Présent' : 'Absent' });
      if (dkim  != null) items.push({ label: 'DKIM',  value: dkim.found  ? 'Présent' : 'Absent' });
      if (dmarc != null) items.push({ label: 'DMARC', value: dmarc.found ? 'Présent' : 'Absent' });
      return items;
    }

    case 'cookies': {
      const issues = d['issues'] as { cookie?: string; issue?: string }[] | string[] | undefined;
      const labels = issues?.map(i => typeof i === 'string' ? i : (i.issue ?? i.cookie ?? ''))
                           .filter(Boolean).slice(0, 3) ?? [];
      return labels.length
        ? [{ label: 'Problèmes', value: labels.join(' · ') }]
        : [{ label: 'Cookies', value: 'Configuration correcte' }];
    }

    case 'cors':
      return d['allow_origin']
        ? [{ label: 'Access-Control-Allow-Origin', value: String(d['allow_origin']).slice(0, 40) }]
        : [{ label: 'CORS', value: 'En-tête absent' }];

    case 'ip':
      return [
        d['ip']           ? { label: 'IP',          value: String(d['ip']) }                                         : null,
        d['total_listed'] != null ? { label: 'Blacklists', value: `${d['total_listed']} liste(s)` }                  : null,
        d['listed_in'] && (d['listed_in'] as string[]).length ? { label: 'Listé dans', value: (d['listed_in'] as string[]).slice(0, 2).join(', ') } : null,
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
      return d['detected']
        ? [{ label: 'WAF détecté', value: String(d['waf_name'] ?? 'Inconnu') }]
        : [{ label: 'WAF', value: 'Non détecté' }];

    case 'tech': {
      const techs = d['technologies'] as string[] | undefined;
      return techs?.length
        ? [{ label: 'Technologies', value: techs.slice(0, 5).join(', ') }]
        : [];
    }

    case 'tls': {
      const protocols = d['supported_protocols'] as string[] | undefined;
      const weak      = d['weak_protocols']      as string[] | undefined;
      const hsts      = d['hsts']                as { present?: boolean } | undefined;
      return [
        protocols?.length ? { label: 'Protocoles',   value: protocols.join(', ') }                   : null,
        weak?.length      ? { label: 'Faibles',       value: weak.join(', ') }                        : null,
        hsts != null      ? { label: 'HSTS',          value: hsts.present ? 'Activé' : 'Désactivé' } : null,
      ].filter(Boolean) as { label: string; value: string }[];
    }

    case 'threat_intel': {
      const cves  = d['cves']       as string[] | undefined;
      const ports = d['open_ports'] as number[] | undefined;
      return [
        ports?.length ? { label: 'Ports ouverts', value: ports.slice(0, 6).join(', ') } : null,
        cves?.length  ? { label: 'CVE détectées', value: `${cves.length}` }              : null,
      ].filter(Boolean) as { label: string; value: string }[];
    }

    case 'http_methods': {
      const dangerous = d['dangerous_allowed'] as string[] | undefined;
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

    case 'takeover': {
      const total     = d['total_checked']    as number | undefined;
      const vuln      = d['total_vulnerable'] as number | undefined;
      const err       = d['error']            as string | undefined;
      if (err) return [{ label: 'Statut', value: 'Aucun sous-domaine à vérifier' }];
      return [
        total != null ? { label: 'Sous-domaines vérifiés',   value: String(total) } : null,
        vuln  != null ? { label: 'Vulnérables',               value: String(vuln)  } : null,
      ].filter(Boolean) as { label: string; value: string }[];
    }

    case 'robots': {
      const sensitive = d['sensitive_disallowed'] as string[] | undefined;
      const sitemaps  = d['sitemaps_declared']    as string[] | undefined;
      return [
        sensitive?.length ? { label: 'Chemins sensibles', value: sensitive.slice(0, 3).join(', ') }   : { label: 'Chemins sensibles', value: 'Aucun' },
        sitemaps?.length  ? { label: 'Sitemap',           value: `${sitemaps.length} déclaré(s)` }     : null,
      ].filter(Boolean) as { label: string; value: string }[];
    }

    case 'open_redirect': {
      const vulnerable = d['vulnerable'] as boolean | undefined;
      const findings   = d['findings']   as unknown[] | undefined;
      return vulnerable
        ? [{ label: 'Redirections', value: `${findings?.length ?? 1} vulnérable(s)` }]
        : [{ label: 'Redirections', value: 'Aucune vulnérable' }];
    }

    case 'directory_listing': {
      const total = d['total_critical'] as number | undefined;
      return total
        ? [{ label: 'Répertoires exposés', value: String(total) }]
        : [{ label: 'Listing', value: 'Aucun répertoire exposé' }];
    }

    default:
      return Object.entries(d)
        .filter(([k, v]) => k !== 'status' && (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean'))
        .slice(0, 3)
        .map(([k, v]) => ({ label: k.replace(/_/g, ' '), value: String(v) }));
  }
}

const EXPLANATIONS: Record<string, Partial<Record<'OK' | 'WARNING' | 'CRITICAL' | 'default', string>>> = {
  ssl: {
    OK:       'Votre certificat SSL/TLS est valide et à jour. Les échanges entre vos visiteurs et votre site sont chiffrés — les données ne peuvent pas être interceptées en clair.',
    WARNING:  'Votre certificat arrive bientôt à expiration ou utilise un protocole vieillissant. Sans renouvellement, les navigateurs afficheront une alerte de sécurité et bloqueront l\'accès à votre site.',
    CRITICAL: 'Votre certificat SSL/TLS est invalide ou expiré. Les navigateurs bloquent l\'accès à votre site et vos visiteurs voient une page d\'erreur. Action urgente requise.',
  },
  headers: {
    OK:       'Vos en-têtes de sécurité HTTP sont correctement configurés. Ils protègent vos visiteurs contre des attaques courantes comme le clickjacking ou l\'injection de contenu.',
    WARNING:  'Certains en-têtes de sécurité HTTP sont manquants. Ces en-têtes sont des lignes de défense côté navigateur — leur absence facilite certaines attaques.',
    CRITICAL: 'Des en-têtes de sécurité critiques sont absents. Votre site est vulnérable à des attaques comme le XSS, le clickjacking ou le vol de session.',
  },
  email: {
    OK:       'Vos enregistrements SPF, DKIM et DMARC sont en place. Ils empêchent des tiers d\'envoyer des emails en se faisant passer pour votre domaine (phishing, spam).',
    WARNING:  'Certains enregistrements de sécurité email sont manquants ou mal configurés. Des attaquants pourraient usurper votre domaine pour envoyer des emails frauduleux à vos clients.',
    CRITICAL: 'Vos protections email sont absentes. N\'importe qui peut envoyer des emails en se faisant passer pour vous — risque élevé de phishing ciblant vos clients.',
  },
  cookies: {
    OK:       'Vos cookies sont correctement sécurisés (flags HttpOnly, Secure, SameSite). Ils ne peuvent pas être volés via JavaScript ou interceptés sur des connexions non-sécurisées.',
    WARNING:  'Certains cookies manquent de flags de sécurité. Un attaquant pourrait potentiellement les voler via du JavaScript malveillant ou les intercepter.',
    CRITICAL: 'Des cookies de session critiques sont exposés sans protection. Un vol de session (session hijacking) est facilement réalisable.',
  },
  cors: {
    OK:       'Votre configuration CORS est restrictive. Seuls les domaines autorisés peuvent faire des requêtes vers votre API depuis un navigateur.',
    WARNING:  'Votre configuration CORS est trop permissive. Des sites tiers pourraient faire des requêtes à votre API au nom de vos utilisateurs connectés.',
    CRITICAL: 'CORS ouvert à tous (`*`). N\'importe quel site web peut interroger votre API en se faisant passer pour un utilisateur authentifié.',
  },
  ip: {
    OK:       'L\'adresse IP de votre serveur n\'est référencée sur aucune liste noire. Votre réputation IP est saine — vos emails ont moins de risques d\'atterrir en spam.',
    WARNING:  'Votre IP est présente sur une ou plusieurs listes noires. Cela peut affecter la délivrabilité de vos emails et nuire à la confiance envers votre domaine.',
    CRITICAL: 'Votre IP est blacklistée sur plusieurs listes. Vos emails sont probablement bloqués et votre site peut être filtré par certains services de sécurité.',
  },
  dns: {
    OK:       'Aucun sous-domaine sensible n\'a été détecté en dehors de ceux attendus. Votre surface d\'attaque DNS est maîtrisée.',
    WARNING:  'Des sous-domaines ont été trouvés — certains pourraient pointer vers des services abandonnés. Un sous-domaine non maintenu peut être réutilisé par un attaquant (subdomain takeover).',
    CRITICAL: 'Des sous-domaines sensibles sont exposés et potentiellement réutilisables. Le risque de subdomain takeover est élevé.',
  },
  cms: {
    OK:       'Aucun CMS détecté en dehors de ce qui est attendu. La surface d\'attaque liée aux CMS est minimisée.',
    WARNING:  'Un CMS a été détecté. Assurez-vous qu\'il est à jour — les CMS populaires sont des cibles fréquentes d\'attaques automatisées.',
    CRITICAL: 'Un CMS obsolète ou mal configuré a été détecté. Des failles connues peuvent être exploitées automatiquement par des scanners malveillants.',
  },
  waf: {
    OK:       'Un pare-feu applicatif (WAF) a été détecté. Il filtre les requêtes malveillantes avant qu\'elles atteignent votre application.',
    WARNING:  'Aucun WAF détecté. Sans pare-feu applicatif, les attaques courantes (SQLi, XSS, scans automatisés) arrivent directement à votre application.',
    CRITICAL: 'Aucun WAF détecté et des vulnérabilités critiques ont été identifiées. Votre application est exposée sans filtrage.',
  },
  tech: {
    OK:       'L\'empreinte technologique de votre site est limitée. Moins un attaquant en sait sur vos technologies, moins il peut cibler des failles spécifiques.',
    WARNING:  'Des technologies et leurs versions sont exposées dans vos en-têtes. Cela permet à un attaquant de rechercher des CVE ciblant vos versions exactes.',
    CRITICAL: 'Des technologies vulnérables ont été identifiées et leurs versions sont exposées. Des exploits publics existent potentiellement pour ces versions.',
  },
  tls: {
    OK:       'Votre configuration TLS est robuste : protocoles modernes uniquement, HSTS activé. Les connexions de vos utilisateurs sont protégées contre le downgrade et l\'interception.',
    WARNING:  'Des protocoles TLS faibles (TLS 1.0/1.1) sont encore supportés. Un attaquant peut forcer une connexion vers un protocole moins sécurisé (downgrade attack).',
    CRITICAL: 'Votre configuration TLS est dangereuse. Des protocoles obsolètes sont actifs et/ou HSTS est absent — les connexions peuvent être interceptées.',
  },
  takeover: {
    OK:       'Aucun sous-domaine vulnérable au takeover détecté. Vos sous-domaines pointent tous vers des services actifs et sous votre contrôle.',
    WARNING:  'Des sous-domaines suspects ont été détectés. Un subdomain takeover permet à un attaquant de prendre le contrôle d\'un sous-domaine de votre marque.',
    CRITICAL: 'Un ou plusieurs sous-domaines sont vulnérables au takeover. Un attaquant peut héberger du contenu malveillant sous votre domaine.',
  },
  threat_intel: {
    OK:       'Aucune menace connue associée à votre infrastructure. Votre IP n\'est pas référencée dans les bases de menaces actives.',
    WARNING:  'Des ports ouverts ou des informations de menace ont été détectés. Chaque port ouvert inutile est une surface d\'attaque supplémentaire.',
    CRITICAL: 'Des CVEs connues et/ou des ports à haut risque ont été détectés sur votre infrastructure. Une exploitation active est possible.',
  },
  http_methods: {
    OK:       'Seules les méthodes HTTP nécessaires sont autorisées. Les méthodes dangereuses (PUT, DELETE, TRACE) sont désactivées.',
    WARNING:  'Des méthodes HTTP potentiellement dangereuses sont activées. TRACE peut faciliter des attaques XST (Cross-Site Tracing).',
    CRITICAL: 'Des méthodes HTTP dangereuses sont actives (PUT, DELETE). Un attaquant peut modifier ou supprimer des ressources sur votre serveur.',
  },
  open_redirect: {
    OK:       'Aucune redirection ouverte détectée. Votre site ne peut pas être utilisé pour rediriger des utilisateurs vers des sites malveillants.',
    WARNING:  'Des redirections potentiellement manipulables ont été détectées. Un attaquant peut créer des liens d\'apparence légitime qui redirigent vers du phishing.',
    CRITICAL: 'Des redirections ouvertes exploitables ont été confirmées. Votre domaine peut être utilisé activement dans des campagnes de phishing.',
  },
  clickjacking: {
    OK:       'Votre site est protégé contre le clickjacking. Un attaquant ne peut pas intégrer votre page dans une iframe invisible pour piéger vos utilisateurs.',
    WARNING:  'La protection anti-clickjacking est partielle ou manquante. Un attaquant peut superposer votre page sous une interface trompeuse.',
    CRITICAL: 'Aucune protection contre le clickjacking. Votre site peut être intégré dans n\'importe quelle page pour piéger vos utilisateurs en leur faisant effectuer des actions à leur insu.',
  },
  directory_listing: {
    OK:       'Le listing de répertoires est désactivé. Les fichiers de votre serveur ne sont pas listables publiquement.',
    WARNING:  'Le listing de répertoires est potentiellement actif sur certains chemins. Des fichiers de configuration ou sensibles pourraient être exposés.',
    CRITICAL: 'Le listing de répertoires est activé. N\'importe qui peut parcourir l\'arborescence de vos fichiers serveur — configs, logs, backups potentiellement exposés.',
  },
  robots: {
    OK:       'Votre fichier robots.txt est correctement configuré. Il guide les moteurs de recherche sans révéler de chemins sensibles.',
    WARNING:  'Votre fichier robots.txt mentionne des chemins sensibles dans les règles `Disallow`. Paradoxalement, cela indique à un attaquant où chercher des pages cachées.',
    CRITICAL: 'Des chemins d\'administration ou sensibles sont exposés dans robots.txt. C\'est une liste de cibles potentielles pour les attaquants.',
  },
  jwt: {
    OK:       'Aucun token JWT exposé ou mal configuré détecté sur vos pages publiques.',
    WARNING:  'Des problèmes de configuration JWT ont été détectés. Des tokens mal signés ou avec une durée de vie excessive peuvent être réutilisés par un attaquant.',
    CRITICAL: 'Des tokens JWT présentent des failles critiques (algorithme `none`, clé faible). Un attaquant peut forger des tokens et usurper l\'identité de vos utilisateurs.',
  },
};

export function getExplanation(key: string, status: 'OK' | 'WARNING' | 'CRITICAL' | null): string {
  const map = EXPLANATIONS[key];
  if (!map) return '';
  return (status && map[status]) ?? map['default'] ?? '';
}

export function getFindings(resultsJson: string | null): Finding[] {
  if (!resultsJson) return [];
  let r: Record<string, Record<string, unknown>>;
  try { r = JSON.parse(resultsJson); } catch { return []; }

  const tier = (r['_meta']?.['tier'] as number) ?? 2;

  return MODULE_META.map(m => {
    const data = r[m.key] ?? {};
    const skipped = tier < m.minTier || Object.keys(data).length === 0;
    const status = skipped ? null : (data['status'] as 'OK' | 'WARNING' | 'CRITICAL' | null ?? null);
    return {
      ...m,
      skipped,
      status,
      summary: skipped ? [] : extractSummary(m.key, data),
      explanation: skipped ? '' : getExplanation(m.key, status),
    };
  });
}
