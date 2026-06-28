export const FEATURES = [
  {
    icon: 'security',
    title: 'Analyse SSL/TLS',
    desc: 'Audit complet des protocoles, chiffrements et certificats. Détection des suites faibles et certificats expirés.',
  },
  {
    icon: 'bug_report',
    title: 'Détection de vulnérabilités',
    desc: 'Headers HTTP dangereux, injections, XSS, CSRF et 15+ vérifications OWASP Top 10.',
  },
  {
    icon: 'dns',
    title: "Prise d'empreinte technologique",
    desc: 'Identification des frameworks, CMS, CDN utilisés — et des CVE connues associées.',
  },
  {
    icon: 'vpn_key',
    title: 'Audit JWT',
    desc: 'Détection des tokens faibles, algorithme alg:none, secrets par défaut et mauvaise expiration.',
  },
  {
    icon: 'warning',
    title: 'Threat Intelligence',
    desc: 'Corrélation avec Shodan InternetDB, bases CVE et réputation IP en temps réel.',
  },
  {
    icon: 'picture_as_pdf',
    title: 'Rapport PDF',
    desc: 'Rapport complet avec score de risque global, findings classés et plan de remédiation.',
  },
  {
    icon: 'link',
    title: 'Scanner URL',
    desc: "Analysez n'importe quelle URL suspecte : phishing, malware, scripts malveillants, domaines blacklistés.",
  },
  {
    icon: 'code',
    title: 'Scan de code',
    desc: 'Analyse statique SAST, détection de secrets, SCA sur vos repositories GitHub publics ou privés.',
  },
  {
    icon: 'policy',
    title: 'Conformité NIS2 / ISO 27001',
    desc: "Auto-évaluation guidée de votre conformité réglementaire avec score et plan d'action exportable en PDF.",
  },
  {
    icon: 'school',
    title: 'Sensibilisation NIS2',
    desc: '17 modules e-learning NIS2 Article 21 pour vos équipes — quiz, gamification, attestations vérifiables et tableau de bord de conformité.',
  },
];

export const TESTIMONIALS = [
  {
    name: 'Sophie M.',
    role: 'CTO, StartupTech',
    avatar: 'S',
    text: "CyberScan nous a permis de détecter une fuite de configuration en production avant qu'elle ne soit exploitée. Indispensable.",
  },
  {
    name: 'Thomas R.',
    role: 'Développeur indépendant',
    avatar: 'T',
    text: "J'utilise le plan Starter pour mes clients. Les rapports PDF sont clairs et je peux les transmettre directement sans explication.",
  },
  {
    name: 'Lucie B.',
    role: 'RSSI, PME industrielle',
    avatar: 'L',
    text: 'Le scan hebdomadaire Business nous donne une visibilité continue sur nos 8 sites. La détection TLS est particulièrement précise.',
  },
  {
    name: 'Marc D.',
    role: 'Responsable SI, cabinet comptable',
    avatar: 'M',
    text: "L'auto-évaluation NIS2 intégrée nous a évité de faire appel à un cabinet externe. Le plan d'action PDF est directement exploitable.",
  },
  {
    name: 'Chloé V.',
    role: 'Lead Dev, agence web',
    avatar: 'C',
    text: 'On livre le rapport CyberScan à chaque client en fin de projet. Ça devient un vrai argument commercial et ça rassure les décideurs.',
  },
  {
    name: 'Antoine P.',
    role: 'Fondateur, SaaS RH',
    avatar: 'A',
    text: "Le scanner de code a trouvé une clé AWS hardcodée dans un vieux fichier de config. Sans CyberScan, on ne l'aurait jamais vu.",
  },
  {
    name: 'Isabelle K.',
    role: 'DRH, ETI industrielle',
    avatar: 'I',
    text: 'Le module de sensibilisation NIS2 est parfait — nos 80 collaborateurs ont complété les formations en 3 semaines. Les attestations générées nous servent directement pour notre audit.',
  },
];

export const FAQS = [
  {
    q: "Qu'est-ce que CyberScan analyse exactement ?",
    a: "CyberScan effectue une analyse non intrusive de votre site : headers de sécurité, configuration SSL/TLS, technologies exposées, JWT, redirections ouvertes, clickjacking, threat intelligence (Shodan, CVE) et bien d'autres vérifications selon votre plan.",
  },
  {
    q: 'Les scans sont-ils intrusifs ou dangereux pour mon site ?',
    a: "Non. Tous les scans sont passifs et non destructifs. Nous analysons les réponses publiques de votre serveur, sans jamais tenter d'exploiter une vulnérabilité.",
  },
  {
    q: 'Comment puis-je recevoir mon rapport ?',
    a: 'Chaque scan génère un rapport PDF téléchargeable depuis votre dashboard. Pour les plans Pro et Business, le rapport est également envoyé automatiquement par email.',
  },
  {
    q: 'Puis-je changer de plan à tout moment ?',
    a: 'Oui. Vous pouvez upgrader ou downgrader votre plan depuis le portail de gestion Stripe accessible dans votre dashboard. Le changement prend effet immédiatement.',
  },
  {
    q: 'Que se passe-t-il si une vulnérabilité critique est détectée ?',
    a: "Le rapport indique clairement le niveau de criticité (OK / WARNING / CRITICAL) avec des recommandations de remédiation pour chaque finding. Pour le plan Business, un email d'alerte est envoyé immédiatement.",
  },
  {
    q: 'Comment fonctionne la facturation ?',
    a: "La facturation est mensuelle, sans engagement, via Stripe. Vous pouvez résilier à tout moment depuis votre portail de gestion. Aucune donnée de paiement n'est stockée sur nos serveurs.",
  },
  {
    q: 'Puis-je analyser une URL suspecte pour savoir si elle est malveillante ?',
    a: "Oui. L'outil Scanner URL disponible dans votre dashboard permet d'analyser n'importe quelle URL en quelques secondes : détection de phishing, malware, scripts malveillants, redirections suspectes et domaines blacklistés. Idéal pour vérifier un lien reçu par email ou message avant de cliquer.",
  },
  {
    q: 'Le scan de code fonctionne-t-il sur des dépôts privés ?',
    a: "Oui. Vous pouvez fournir un Personal Access Token GitHub pour analyser vos repositories privés. Le token est utilisé uniquement pendant le scan et n'est jamais stocké sur nos serveurs.",
  },
  {
    q: "CyberScan peut-il m'aider pour ma conformité NIS2 ou ISO 27001 ?",
    a: "Oui. L'outil d'auto-évaluation NIS2 et ISO 27001 vous guide item par item et génère un rapport PDF de conformité avec un score et un plan d'action. Il ne remplace pas un audit légal, mais constitue un excellent point de départ pour structurer votre démarche.",
  },
  {
    q: 'Mes données de scan sont-elles confidentielles ?',
    a: 'Oui. Les résultats de vos scans sont strictement privés et accessibles uniquement à vous depuis votre dashboard. Nous ne revendons aucune donnée à des tiers. Les données sont hébergées en Europe (AWS EU-West-3, Paris) et chiffrées au repos.',
  },
];

export const AUDIT_OFFERS = [
  {
    icon: 'flash_on',
    name: 'Audit Flash',
    target: 'Sites vitrines, blogs, indépendants',
    price: '390 €',
    duration: '0,5 jour',
    badge: '',
    featured: false,
    cta: 'Prendre rendez-vous',
    items: [
      'Scan de vulnérabilités externes (OWASP ZAP)',
      'Analyse SSL/TLS (SSL Labs)',
      'Vérification des headers HTTP',
      'Scan de ports (Nmap)',
      'Rapport synthétique 3-5 pages (score A→F)',
    ],
  },
  {
    icon: 'manage_search',
    name: 'App-Check',
    target: 'SaaS, applications métier, e-commerce complexe',
    price: '990 €',
    duration: '1,5 jour',
    badge: 'Le plus demandé',
    featured: true,
    cta: 'Réserver cet audit',
    items: [
      "Tout l'Audit Flash +",
      'Revue de code source (si accès)',
      'Tests API (SQLi, XSS, IDOR, CSRF)',
      'Gestion sessions / tokens JWT',
      'Contrôles RGPD',
      'Rapport 20-30 pages',
      'Atelier restitution 1 h',
      'Plan de remédiation chiffré',
    ],
  },
  {
    icon: 'bug_report',
    name: 'Pentest léger',
    target: 'E-commerce, données sensibles, obligations légales',
    price: '2 490 €',
    duration: '4 jours',
    badge: '',
    featured: false,
    cta: 'Réserver cet audit',
    items: [
      "Tout l'App-Check +",
      "Tests d'intrusion actifs",
      "Proof of concept d'exploitation",
      'Escalade de privilèges',
      'Rapport technique + version dirigeant',
      'Présentation au COMEX si besoin',
    ],
  },
  {
    icon: 'policy',
    name: 'Audit NIS2 / RGPD',
    target: 'Entités essentielles ou importantes NIS2',
    price: '1 290 €',
    duration: '2 jours',
    badge: 'Nouveau',
    featured: false,
    cta: 'Prendre rendez-vous',
    items: [
      'Cartographie des traitements de données',
      'Analyse des écarts NIS2 (34 contrôles)',
      'Revue des contrats sous-traitants (DPA)',
      'Plan de remédiation priorisé',
      'Rapport de conformité certifiable',
      'Accompagnement déclaration CNIL si incident',
    ],
  },
];

export const NEWSLETTER_AVATARS = [
  { initials: 'ML', bg: '#0e7490', color: '#fff' },
  { initials: 'PD', bg: '#7c3aed', color: '#fff' },
  { initials: 'SB', bg: '#0f766e', color: '#fff' },
  { initials: 'AR', bg: '#b45309', color: '#fff' },
  { initials: 'JC', bg: '#be185d', color: '#fff' },
];

export const NEWSLETTER_ITEMS = [
  {
    emoji: '🌍',
    bg: 'rgba(239,68,68,0.15)',
    title: 'Flash International',
    desc: "Une cyberattaque majeure décryptée avec l'impact estimé et le risque pour votre secteur",
  },
  {
    emoji: '💡',
    bg: 'rgba(34,211,238,0.15)',
    title: 'Le Bon Réflexe',
    desc: 'Une pratique concrète en 2 minutes qui bloque 80% des attaques courantes',
  },
  {
    emoji: '⚖️',
    bg: 'rgba(168,85,247,0.15)',
    title: 'Coin des Dirigeants',
    desc: 'Réglementation française, NIS2, RGPD — ce que vous devez savoir chaque mois',
  },
];

export const COMPARISON_ROWS = [
  { label: 'Sites surveillés', starter: '1', pro: '3', business: '10', enterprise: 'Illimités' },
  {
    label: 'Fréquence des scans',
    starter: 'Mensuel',
    pro: 'Hebdomadaire',
    business: 'Quotidien',
    enterprise: 'Temps réel',
  },
  { label: 'Rapport PDF', starter: true, pro: true, business: true, enterprise: true },
  { label: 'Headers & SSL', starter: true, pro: true, business: true, enterprise: true },
  { label: 'Scanner URL', starter: true, pro: true, business: true, enterprise: true },
  {
    label: 'TLS audit / Threat Intel',
    starter: false,
    pro: true,
    business: true,
    enterprise: true,
  },
  {
    label: 'JWT / Clickjacking / Redirects',
    starter: false,
    pro: false,
    business: true,
    enterprise: true,
  },
  { label: 'Scan de code (SAST/SCA)', starter: false, pro: true, business: true, enterprise: true },
  {
    label: 'Conformité NIS2 / ISO 27001',
    starter: false,
    pro: true,
    business: true,
    enterprise: true,
  },
  { label: 'Alerte email CRITICAL', starter: false, pro: true, business: true, enterprise: true },
  { label: 'Alerte SSL expiration', starter: false, pro: true, business: true, enterprise: true },
  {
    label: 'Rapport blanc (logo client)',
    starter: false,
    pro: false,
    business: true,
    enterprise: true,
  },
  { label: 'Accès API REST', starter: false, pro: false, business: false, enterprise: true },
  {
    label: 'Webhooks & intégrations',
    starter: false,
    pro: false,
    business: false,
    enterprise: true,
  },
  { label: 'Account manager dédié', starter: false, pro: false, business: false, enterprise: true },
  {
    label: 'Support prioritaire 24h',
    starter: false,
    pro: false,
    business: true,
    enterprise: true,
  },
];

export const TRUST_ITEMS = [
  {
    icon: 'storage',
    q: 'Où sont mes données ?',
    a: 'Hébergées exclusivement sur AWS Paris (eu-west-3), France. Aucun transfert hors Union Européenne.',
  },
  {
    icon: 'lock',
    q: "C'est sécurisé ?",
    a: 'Score A+ sur Mozilla Observatory. Chiffrement AES-256 au repos, TLS 1.3 en transit.',
  },
  {
    icon: 'manage_accounts',
    q: 'Qui accède à mon historique ?',
    a: "Accès restreint par IAM avec MFA obligatoire. Vos rapports ne sont accessibles qu'à votre compte.",
  },
  {
    icon: 'support_agent',
    q: 'Et si ça bug ?',
    a: "Support sous 24h pour les abonnés payants. Notification obligatoire en cas d'incident (RGPD/NIS 2) sous 72h.",
  },
];

export const ARCH_STEPS = [
  {
    icon: 'send',
    label: 'Requête API',
    desc: 'Votre demande de scan arrive via HTTPS sur notre API FastAPI.',
  },
  {
    icon: 'workspaces',
    label: 'Conteneur isolé',
    desc: 'Un conteneur éphémère est lancé uniquement pour votre analyse.',
  },
  {
    icon: 'analytics',
    label: '21 modules',
    desc: "Les modules s'exécutent en isolation, sans accès aux données des autres clients.",
  },
  {
    icon: 'delete_sweep',
    label: 'Autodestruction',
    desc: 'Le conteneur est détruit. Seul le rapport JSON chiffré est conservé.',
  },
];

export const COMPLIANCE_ITEMS = [
  {
    icon: 'gavel',
    title: 'RGPD',
    desc: "Registre des traitements tenu. Droit à l'oubli : supprimez vos scans en un clic depuis votre dashboard.",
  },
  {
    icon: 'policy',
    title: 'NIS 2',
    desc: "Signalement d'incident en moins de 72h si votre compte est affecté. Obligations respectées.",
  },
];

export const HOW_IT_WORKS = [
  {
    step: '01',
    icon: 'link',
    title: 'Entrez votre URL',
    desc: "Renseignez l'adresse de votre site ou de l'URL suspecte à analyser. Aucune installation requise.",
  },
  {
    step: '02',
    icon: 'radar',
    title: 'Analyse automatique',
    desc: 'Nos 21 modules passent votre site au crible en 2 minutes : SSL, headers, ports, CVE, threat intel et bien plus.',
  },
  {
    step: '03',
    icon: 'picture_as_pdf',
    title: "Rapport PDF + plan d'action",
    desc: 'Téléchargez un rapport complet avec score de risque, liste des findings et recommandations de remédiation.',
  },
];

export const USE_CASES = [
  {
    icon: 'rocket_launch',
    color: 'text-cyan-400',
    bg: 'bg-cyan-900/20 border-cyan-800/40',
    title: 'Startups & SaaS',
    desc: 'Sécurisez votre MVP avant le lancement. Montrez à vos investisseurs que la sécurité est prise au sérieux dès le Day 1.',
    points: ['Audit pré-lancement', 'Rapport pour due diligence', 'Conformité RGPD dès le départ'],
  },
  {
    icon: 'web',
    color: 'text-violet-400',
    bg: 'bg-violet-900/20 border-violet-800/40',
    title: 'Agences web',
    desc: 'Livrez un rapport de sécurité avec chaque projet client. Différenciez-vous et couvrez votre responsabilité.',
    points: [
      'Rapport blanc à votre logo',
      'Scan en fin de projet',
      'Argument commercial différenciant',
    ],
  },
  {
    icon: 'business',
    color: 'text-amber-400',
    bg: 'bg-amber-900/20 border-amber-800/40',
    title: 'PME & ETI',
    desc: "Surveillez vos sites en continu sans recruter un expert. Recevez une alerte dès qu'une faille est détectée.",
    points: ['Surveillance continue', 'Alertes email CRITICAL', 'Conformité NIS2 guidée'],
  },
  {
    icon: 'shopping_cart',
    color: 'text-green-400',
    bg: 'bg-green-900/20 border-green-800/40',
    title: 'E-commerce',
    desc: 'Protégez les données de paiement de vos clients. Évitez les fuites de données et les sanctions CNIL.',
    points: ['Analyse cookies & CORS', 'Détection de skimmers', 'Conformité PCI-DSS partielle'],
  },
];

export const CYBER_STATS = [
  {
    value: '4,88 M$',
    label: "Coût moyen d'une violation de données en 2024",
    source: 'IBM Cost of a Data Breach 2024',
  },
  {
    value: '194 jours',
    label: "Délai moyen avant détection d'une intrusion",
    source: 'Mandiant M-Trends 2024',
  },
  {
    value: '82 %',
    label: 'Des violations impliquent une erreur humaine ou une mauvaise config',
    source: 'Verizon DBIR 2024',
  },
  {
    value: '14,90 €',
    label: "Le prix d'un abonnement Surveillance Starter par mois",
    source: 'CyberScan',
  },
];
