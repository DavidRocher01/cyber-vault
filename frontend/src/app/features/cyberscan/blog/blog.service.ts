import { Injectable } from '@angular/core';

export interface BlogArticle {
  slug: string;
  title: string;
  description: string;
  date: string;
  readTime: number;
  category: string;
  tags: string[];
  htmlContent: string;
}

@Injectable({ providedIn: 'root' })
export class BlogService {
  private readonly articles: BlogArticle[] = [
    {
      slug: 'audit-cybersecurite-pme-prix-2026',
      title: 'Audit cybersécurité PME : combien ça coûte vraiment en 2026 ?',
      description: 'Tarifs détaillés, types d\'audits, ce qui est inclus et le ROI pour une TPE/PME. Guide complet par un développeur-auditeur basé en Auvergne-Rhône-Alpes.',
      date: '2026-05-01',
      readTime: 8,
      category: 'Audit & Conseils',
      tags: ['audit cybersécurité', 'PME', 'prix', 'pentest', 'RGPD'],
      htmlContent: `
<p>En 2026, les TPE/PME représentent plus de 60 % des victimes de cyberattaques recensées en France. Pourtant, beaucoup pensent encore que leur taille les protège. C'est l'inverse : les PME sont ciblées précisément parce qu'elles ont moins de ressources de sécurité et des systèmes souvent plus anciens.</p>
<p>La question n'est plus "va-t-on être attaqués ?" mais "quand, et avec quel impact ?"</p>

<h2>Les 4 types d'audits de sécurité</h2>

<h3>1. Audit Flash — le premier pas (à partir de 245 € HT)</h3>
<p>Idéal pour un site vitrine, un blog professionnel ou un site e-commerce simple. En une demi-journée :</p>
<ul>
  <li>Analyse SSL/TLS — certificat, configuration, grade (A à F)</li>
  <li>Headers HTTP de sécurité — CSP, HSTS, X-Frame-Options, Referrer-Policy</li>
  <li>Détection des technologies exposées et versions vulnérables (CMS, frameworks)</li>
  <li>Réputation IP et présence sur les blacklists</li>
  <li>Configuration DNS — SPF, DKIM, DMARC</li>
  <li>Cookies et gestion des sessions</li>
</ul>
<p><strong>Livrable :</strong> rapport PDF de 8 à 12 pages + plan d'action priorisé sous 24 h.</p>
<p><em>Pour qui ?</em> Artisans, professions libérales, collectivités, sites vitrines e-commerce.</p>

<h3>2. Audit App-Check — pour les applications web (725 € HT)</h3>
<p>Pensé pour les SaaS, applications métier et plateformes e-commerce complexes. Durée : 1,5 jour.</p>
<ul>
  <li>Tout l'Audit Flash +</li>
  <li>Revue de code source (si accès fourni)</li>
  <li>Tests des endpoints API — authentification, autorisation, injections (SQLi, NoSQLi)</li>
  <li>Gestion des sessions et tokens JWT</li>
  <li>Contrôles RGPD — données personnelles, bases légales, formulaires de consentement</li>
  <li>Tests Cross-Site Scripting (XSS) et CSRF</li>
</ul>
<p><strong>Livrable :</strong> rapport de 20 à 30 pages + atelier restitution 1 h + plan de remédiation chiffré.</p>
<p><em>Pour qui ?</em> Startups SaaS, agences e-commerce, éditeurs de logiciels.</p>

<h3>3. Pentest léger — simulation d'attaque (1 900 € HT)</h3>
<p>Pour les e-commerces gérant des données de paiement, les cabinets médicaux, juridiques, ou tout acteur traitant des données sensibles. Durée : 4 jours.</p>
<ul>
  <li>Tout l'App-Check +</li>
  <li>Tests d'intrusion actifs (avec accord écrit préalable)</li>
  <li>Exploitation des vulnérabilités trouvées (proof of concept)</li>
  <li>Escalade de privilèges et mouvement latéral</li>
  <li>Rapport technique + rapport exécutif (version dirigeant)</li>
</ul>
<p><em>Pour qui ?</em> E-commerces, cabinets médicaux/juridiques, établissements financiers.</p>

<h3>4. Pentest complet (sur devis, à partir de 8 000 € HT)</h3>
<p>Pour les structures ayant des obligations réglementaires fortes — NIS2, ISO 27001, PCI-DSS — ou des actifs critiques à protéger.</p>

<h2>Les abonnements de surveillance continue</h2>
<p>Un audit ponctuel est un instantané. Votre application évolue, de nouvelles vulnérabilités sont publiées chaque jour (CVE). Les abonnements permettent une détection en continu :</p>
<ul>
  <li><strong>Vigie (~120 €/mois)</strong> — scan hebdomadaire automatisé + alerte immédiate en cas de nouveau risque</li>
  <li><strong>Sentinelle (~350 €/mois)</strong> — scan quotidien + rapport mensuel + ligne directe en cas d'incident</li>
  <li><strong>Blindage 360 (~950 €/mois)</strong> — surveillance continue + audit trimestriel + revue de code mensuelle</li>
</ul>

<h2>Le vrai coût d'une faille non détectée</h2>
<p>Une violation de données RGPD peut entraîner :</p>
<ul>
  <li><strong>Amende CNIL</strong> — jusqu'à 4 % du chiffre d'affaires annuel mondial (article 83 RGPD)</li>
  <li><strong>Notification obligatoire</strong> — 72 h après détection pour signaler à la CNIL (article 33 RGPD)</li>
  <li><strong>Frais de réponse à incident</strong> — estimés entre 15 000 et 50 000 € pour une PME</li>
  <li><strong>Atteinte à la réputation</strong> — perte de confiance clients, couverture presse négative</li>
</ul>
<p>En comparaison, un audit Flash à 490 € représente une prime d'assurance. Le ROI moyen d'un audit de sécurité est estimé à <strong>10× sur 3 ans</strong> selon les études du secteur.</p>

<h2>Comment choisir votre type d'audit ?</h2>
<table>
  <thead><tr><th>Votre situation</th><th>Audit recommandé</th><th>Budget</th></tr></thead>
  <tbody>
    <tr><td>Site vitrine / blog professionnel</td><td>Flash</td><td>245 € HT</td></tr>
    <tr><td>Application SaaS / e-commerce</td><td>App-Check</td><td>725 € HT</td></tr>
    <tr><td>Données sensibles / obligation légale</td><td>Pentest léger</td><td>1 900 € HT</td></tr>
    <tr><td>Surveillance continue</td><td>Abonnement Sentinelle</td><td>350 € HT/mois</td></tr>
  </tbody>
</table>

<h2>Pourquoi choisir un développeur-auditeur ?</h2>
<p>La plupart des auditeurs de sécurité ont un profil soit purement offensif (pentest), soit organisationnel (RSSI/consultant). Un développeur full-stack qui pratique aussi l'audit de sécurité apporte une valeur différente :</p>
<ul>
  <li>Il <strong>lit votre code</strong> et comprend vos contraintes métier</li>
  <li>Ses recommandations sont <strong>implémentables immédiatement</strong>, pas juste théoriques</li>
  <li>Il peut <strong>corriger directement</strong> les failles trouvées si besoin (option)</li>
  <li>Il comprend les architectures modernes — APIs REST, JWT, Angular, React, FastAPI, Django</li>
</ul>

<h2>Comment se déroule un audit ?</h2>
<ol>
  <li><strong>Appel découverte (30 min)</strong> — cadrage de la mission, périmètre, modalités</li>
  <li><strong>Accord de confidentialité</strong> — NDA signé avant tout accès</li>
  <li><strong>Réalisation de l'audit</strong> — tests techniques selon le type choisi</li>
  <li><strong>Rapport et restitution</strong> — remise du PDF + appel de présentation des résultats</li>
  <li><strong>Suivi (inclus 30 jours)</strong> — questions, clarifications, vérification des corrections</li>
</ol>

<p>Vous êtes une TPE/PME en Auvergne-Rhône-Alpes et souhaitez évaluer votre exposition aux cybermenaces ? Commencez par un scan gratuit de votre site, ou réservez directement un appel découverte de 15 minutes.</p>
      `,
    },
    {
      slug: 'vulnerabilites-courantes-sites-ecommerce',
      title: 'Les 10 vulnérabilités les plus courantes sur les sites e-commerce français',
      description: 'XSS, injection SQL, mauvaise config SSL... Les failles que l\'on trouve à 90 % sur les sites e-commerce lors de nos audits. Exemples concrets et solutions.',
      date: '2026-05-12',
      readTime: 10,
      category: 'Sécurité Web',
      tags: ['e-commerce', 'XSS', 'injection SQL', 'OWASP', 'sécurité web'],
      htmlContent: `
<p>Lors de chaque audit de site e-commerce, nous retrouvons les mêmes familles de vulnérabilités. Pas parce que les développeurs sont négligents — mais parce que la pression des délais, les frameworks mal configurés par défaut et l'absence de culture sécurité créent des angles morts systématiques.</p>
<p>Voici les 10 vulnérabilités que nous trouvons lors de <strong>plus de 90 % de nos audits</strong> sur des boutiques en ligne françaises.</p>

<h2>#1 — Certificat SSL mal configuré (grade B ou moins)</h2>
<p>Un cadenas dans la barre d'adresse ne suffit pas. La vraie question : quelle est la configuration TLS derrière ? Les erreurs les plus fréquentes :</p>
<ul>
  <li>Support de TLS 1.0 ou 1.1 (protocoles obsolètes depuis 2020)</li>
  <li>Algorithmes de chiffrement faibles (RC4, 3DES)</li>
  <li>Certificat expiré ou sur le point d'expirer</li>
  <li>HSTS (HTTP Strict Transport Security) absent</li>
</ul>
<p><strong>Impact :</strong> interception des communications (attaque man-in-the-middle), déclassement SEO Google, méfiance des navigateurs.</p>
<p><strong>Solution :</strong> test SSL Labs (ssllabs.com), configuration via Nginx/Apache avec TLS 1.2+ uniquement, activation HSTS avec <code>max-age=31536000</code>.</p>

<h2>#2 — Headers HTTP de sécurité manquants</h2>
<p>Ces en-têtes HTTP indiquent au navigateur comment traiter votre page. Sans eux, vos visiteurs sont exposés à des attaques côté client.</p>
<ul>
  <li><strong>Content-Security-Policy (CSP)</strong> — absente sur 78 % des sites audités. Permet les attaques XSS.</li>
  <li><strong>X-Frame-Options</strong> — absente sur 65 % des sites. Permet le clickjacking.</li>
  <li><strong>X-Content-Type-Options</strong> — absente sur 55 % des sites. Permet le MIME sniffing.</li>
  <li><strong>Referrer-Policy</strong> — non configurée, fuit des informations sensibles aux tiers.</li>
  <li><strong>Permissions-Policy</strong> — rarement configurée, expose l'accès caméra/micro/géoloc.</li>
</ul>
<p><strong>Solution :</strong> configuration au niveau serveur (Nginx, Apache, CloudFront) ou via middleware applicatif. Outil de test : securityheaders.com.</p>

<h2>#3 — Injection SQL dans les formulaires</h2>
<p>La faille OWASP A03:2021. Toujours présente en 2026, notamment sur les sites utilisant des plugins WordPress ou PrestaShop anciens. Un payload aussi simple que <code>' OR 1=1 --</code> peut extraire toute la base de données clients.</p>
<p><strong>Impact :</strong> extraction de toutes les données (commandes, cartes, mots de passe), modification ou suppression des données.</p>
<p><strong>Solution :</strong> requêtes préparées (prepared statements), ORM correctement utilisé, validation stricte des entrées côté serveur, WAF.</p>

<h2>#4 — XSS reflété dans les paramètres d'URL</h2>
<p>Un attaquant envoie à votre client un lien contenant du code JavaScript malveillant. Quand le client clique, le script s'exécute dans son navigateur avec les droits de votre site (session, cookies).</p>
<p>Exemple : <code>https://boutique.fr/recherche?q=&lt;script&gt;...&lt;/script&gt;</code></p>
<p><strong>Impact :</strong> vol de session, redirection vers phishing, injection de faux formulaires de paiement.</p>
<p><strong>Solution :</strong> encodage systématique des sorties HTML, CSP stricte, validation des entrées.</p>

<h2>#5 — Version de CMS ou de plugin exposée</h2>
<p>WooCommerce 7.x avec un plugin de paiement non mis à jour contenant une CVE connue : voilà une attaque automatisée en quelques heures. Les scanners automatiques cherchent en permanence les versions vulnérables.</p>
<p><strong>Impact :</strong> exploitation ciblée de CVE publiques, escalade de privilèges, backdoor installée.</p>
<p><strong>Solution :</strong> masquer les numéros de version (headers, meta generator), mises à jour automatiques, veille CVE.</p>

<h2>#6 — Accès à l'administration sans second facteur (2FA)</h2>
<p>Le panneau d'administration de votre boutique est accessible à <code>/wp-admin</code>, <code>/admin</code> ou <code>/back-office</code> avec uniquement un login/mot de passe. Une attaque par credential stuffing (listes de mots de passe issus de fuites) peut compromettre le compte en minutes.</p>
<p><strong>Impact :</strong> prise de contrôle totale de la boutique, injection de code malveillant, vol de données clients.</p>
<p><strong>Solution :</strong> 2FA obligatoire sur tous les accès admin, restriction IP, URL d'administration personnalisée.</p>

<h2>#7 — Secrets dans le code JavaScript frontend</h2>
<p>Clés API Stripe, tokens d'accès, credentials Firebase... Il est fréquent de trouver ces secrets dans le bundle JavaScript servi au navigateur. Un simple <code>Ctrl+U</code> suffit pour les découvrir.</p>
<p><strong>Impact :</strong> utilisation frauduleuse des APIs (frais à votre charge), accès à des données internes.</p>
<p><strong>Solution :</strong> jamais de secrets dans le frontend, utilisation de variables d'environnement côté serveur uniquement, audit régulier avec des outils comme <code>gitleaks</code> ou <code>trufflehog</code>.</p>

<h2>#8 — CORS mal configuré</h2>
<p>Un CORS avec <code>Access-Control-Allow-Origin: *</code> sur une API authentifiée, ou pire un CORS qui reflète n'importe quelle origine, expose vos endpoints à des requêtes cross-site malveillantes.</p>
<p><strong>Impact :</strong> accès non autorisé à l'API depuis n'importe quel site tiers, extraction de données utilisateur.</p>
<p><strong>Solution :</strong> whitelist explicite des origines autorisées, CORS restrictif sur les endpoints sensibles.</p>

<h2>#9 — Mauvaise gestion des sessions</h2>
<p>Cookie de session sans attributs <code>Secure</code>, <code>HttpOnly</code> et <code>SameSite=Strict</code>. Tokens JWT avec algorithme <code>none</code> accepté. Sessions qui ne sont pas invalidées à la déconnexion.</p>
<p><strong>Impact :</strong> vol de session, authentification bypassed, persistance après déconnexion.</p>
<p><strong>Solution :</strong> attributs cookie stricts, algorithme JWT fort (RS256 minimum), invalidation serveur des tokens à la déconnexion.</p>

<h2>#10 — Absence de rate limiting</h2>
<p>Sans protection contre les tentatives multiples, votre formulaire de login, de réinitialisation de mot de passe ou votre API de paiement est vulnérable au brute force.</p>
<p><strong>Impact :</strong> compromission de comptes par force brute, abus de vos API, surcoût serveur (DoS applicatif).</p>
<p><strong>Solution :</strong> rate limiting par IP et par compte (ex : 5 tentatives / 15 min), CAPTCHA sur les formulaires sensibles, verrouillage temporaire.</p>

<h2>Ce que ça signifie pour vous</h2>
<p>Si votre site e-commerce présente 3 de ces 10 vulnérabilités, il est potentiellement exploitable aujourd'hui. Les attaques automatisées ne ciblent pas les entreprises — elles ciblent les vulnérabilités. Et les scanners automatiques tournent 24/7.</p>
<p>Un audit Flash (245 € HT, demi-journée) permet de vérifier tous ces points et de recevoir un plan d'action priorisé sous 24 h. <strong>Le coût d'une fuite de données clients dépasse systématiquement les 15 000 €</strong> pour une PME — sans compter l'amende CNIL et l'atteinte à la réputation.</p>
<p>Commencez par un scan gratuit de votre site pour avoir une première indication.</p>
      `,
    },
  ];

  getAll(): BlogArticle[] {
    return [...this.articles].sort((a, b) => b.date.localeCompare(a.date));
  }

  getBySlug(slug: string): BlogArticle | undefined {
    return this.articles.find(a => a.slug === slug);
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
  }
}
