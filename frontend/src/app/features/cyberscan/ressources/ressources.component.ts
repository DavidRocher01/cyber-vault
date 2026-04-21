import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { Title, Meta } from '@angular/platform-browser';
import { DOCUMENT } from '@angular/common';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    standalone: true,
    selector: 'app-ressources',
    imports: [RouterLink, MatIconModule, MatButtonModule, NavButtonsComponent],
    templateUrl: './ressources.component.html'
})
export class RessourcesComponent {
  private titleService = inject(Title);
  private meta = inject(Meta);
  private doc = inject(DOCUMENT);

  constructor() {
    this.titleService.setTitle('Ressources cybersécurité — CyberScan');
    this.meta.updateTag({ name: 'description', content: 'Outils, plateformes et chaînes YouTube sélectionnés pour approfondir vos connaissances en cybersécurité : audits, gouvernance, RGPD, CTF.' });
    this.meta.updateTag({ property: 'og:title', content: 'Ressources cybersécurité — CyberScan' });
    this.meta.updateTag({ property: 'og:description', content: 'Outils, plateformes et chaînes YouTube pour approfondir vos connaissances en cybersécurité.' });
    this.meta.updateTag({ property: 'og:url', content: 'https://cyberscanapp.com/cyberscan/ressources' });
    this.meta.updateTag({ property: 'og:type', content: 'website' });
    this._setCanonical('https://cyberscanapp.com/cyberscan/ressources');
  }

  private _setCanonical(url: string): void {
    let link = this.doc.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (!link) {
      link = this.doc.createElement('link');
      link.setAttribute('rel', 'canonical');
      this.doc.head.appendChild(link);
    }
    link.setAttribute('href', url);
  }

  categories = [
    {
      icon: 'terminal',
      title: 'Lab Technique — SecDevOps & Audit',
      subtitle: 'Pour les développeurs, administrateurs et pentesters',
      iconClass: 'text-cyan-400',
      links: [
        { name: 'Any.Run', desc: 'Sandbox interactive : observer un malware s\'exécuter en temps réel dans une VM', url: 'https://any.run', badge: 'Sandbox' },
        { name: 'Joe Sandbox', desc: 'Analyse profonde de fichiers et d\'URL pour détecter des comportements malveillants sophistiqués', url: 'https://www.joesandbox.com', badge: 'Sandbox' },
        { name: 'Shodan', desc: 'Le "moteur de recherche des objets connectés" : tout ce qui est exposé sur internet', url: 'https://www.shodan.io', badge: 'Reconnaissance' },
        { name: 'VirusTotal', desc: 'Analyse de fichiers, URL, IP et domaines avec 70+ moteurs antivirus simultanément', url: 'https://www.virustotal.com', badge: 'Analyse' },
        { name: 'Root-Me', desc: 'Apprendre le hacking éthique via des exercices progressifs et des CTF', url: 'https://www.root-me.org', badge: 'CTF' },
        { name: 'TryHackMe', desc: 'Parcours guidés pour la cybersécurité offensive et défensive', url: 'https://tryhackme.com', badge: 'CTF' },
        { name: 'HackTheBox', desc: 'Challenges avancés et labs réalistes pour pratiquer la sécurité offensive', url: 'https://www.hackthebox.com', badge: 'CTF' },
        { name: 'Google Security Blog', desc: 'Vision de pointe sur la sécurisation des infrastructures à grande échelle', url: 'https://security.googleblog.com', badge: 'Veille' },
        { name: 'CVE Details', desc: 'Base de données détaillée des CVE avec scores CVSS, références et exploits connus', url: 'https://www.cvedetails.com', badge: 'CVE' },
        { name: 'Exploit-DB', desc: 'Archive publique des exploits et vulnérabilités documentées, maintenue par Offensive Security', url: 'https://www.exploit-db.com', badge: 'Exploit' },
      ],
    },
    {
      icon: 'gavel',
      title: 'Gouvernance & Conformité',
      subtitle: 'Pour les managers, DPO et responsables RSSI',
      iconClass: 'text-purple-400',
      links: [
        { name: 'ANSSI — Cyber-Guide', desc: 'Fiches pratiques pour mettre en place une hygiène informatique en entreprise', url: 'https://www.ssi.gouv.fr/guide/la-cybersecurite-pour-les-tpe-pme-en-12-questions/', badge: 'ANSSI' },
        { name: 'ANSSI — Guides PRIS', desc: 'Référentiels de sécurité pour les prestataires de détection et de réponse à incidents', url: 'https://www.ssi.gouv.fr/entreprise/qualifications/', badge: 'ANSSI' },
        { name: 'CNIL — Sécurité des données', desc: 'Guide indispensable pour lier technique et obligations légales (RGPD)', url: 'https://www.cnil.fr/fr/securite-informatique', badge: 'RGPD' },
        { name: 'Cybermalveillance.gouv.fr', desc: 'Supports prêts à l\'emploi pour sensibiliser vos collaborateurs', url: 'https://www.cybermalveillance.gouv.fr', badge: 'Sensibilisation' },
        { name: 'NIST Cybersecurity Framework', desc: 'Le référentiel américain de gestion des risques cyber adopté mondialement', url: 'https://www.nist.gov/cyberframework', badge: 'Framework' },
        { name: 'ISO 27001 Overview', desc: 'Présentation officielle de la norme ISO/IEC 27001:2022 pour la gestion de la sécurité de l\'information', url: 'https://www.iso.org/standard/27001', badge: 'ISO 27001' },
        { name: 'Observatoire du FIC', desc: 'Analyses macro sur les tendances de la cybercriminalité et enjeux géopolitiques', url: 'https://www.forum-fic.com', badge: 'Stratégie' },
      ],
    },
    {
      icon: 'public',
      title: 'Visualisation des Menaces',
      subtitle: 'Rendre la cybermenace concrète et pédagogique',
      iconClass: 'text-orange-400',
      links: [
        { name: 'Kaspersky Cyberthreat Map', desc: 'Carte mondiale des attaques en temps réel — idéal pour illustrer l\'ampleur du trafic malveillant', url: 'https://cybermap.kaspersky.com', badge: 'Carte' },
        { name: 'Shodan Maps', desc: 'Visualisation géographique des équipements mal sécurisés exposés sur internet', url: 'https://maps.shodan.io', badge: 'Carte' },
        { name: 'Threatmap Check Point', desc: 'Dashboard temps réel des cyberattaques mondiales par type (malware, DDoS, phishing)', url: 'https://threatmap.checkpoint.com', badge: 'Carte' },
        { name: 'MITRE ATT&CK', desc: 'Matrice de tactiques et techniques utilisées par les groupes APT — référence universelle pour le threat modeling', url: 'https://attack.mitre.org', badge: 'Framework' },
      ],
    },
    {
      icon: 'shield',
      title: 'Éthique & Vie Privée',
      subtitle: 'La cybersécurité, c\'est aussi la défense des libertés numériques',
      iconClass: 'text-green-400',
      links: [
        { name: 'Privacy Guides', desc: 'Recommandations d\'outils (navigateurs, VPN, messageries) axées sur la confidentialité', url: 'https://www.privacyguides.org/fr/', badge: 'Vie privée' },
        { name: 'Electronic Frontier Foundation', desc: 'Pour l\'aspect juridique et politique de la sécurité et de la cryptographie', url: 'https://www.eff.org', badge: 'Droits' },
        { name: 'No More Ransom', desc: 'Clés de déchiffrement gratuites pour les victimes de ransomwares', url: 'https://www.nomoreransom.org/fr/index.html', badge: 'Urgence' },
        { name: 'PhishTank', desc: 'Base de données collaborative des sites de phishing signalés', url: 'https://www.phishtank.com', badge: 'Phishing' },
        { name: 'Have I Been Pwned', desc: 'Vérifiez si votre email ou mot de passe figure dans une fuite de données connue', url: 'https://haveibeenpwned.com', badge: 'Breach' },
      ],
    },
    {
      icon: 'build',
      title: 'Outils Open Source Recommandés',
      subtitle: 'Pour auditer, détecter et sécuriser vos infrastructures',
      iconClass: 'text-amber-400',
      links: [
        { name: 'OWASP ZAP', desc: 'Scanner de vulnérabilités web activement maintenu par OWASP — détection automatique XSS, SQLi, etc.', url: 'https://www.zaproxy.org', badge: 'Scanner' },
        { name: 'Nmap', desc: 'La référence du scan réseau : découverte d\'hôtes, détection de services et d\'OS', url: 'https://nmap.org', badge: 'Réseau' },
        { name: 'Nikto', desc: 'Scanner de serveurs web : détecte fichiers dangereux, versions obsolètes, mauvaises configurations', url: 'https://cirt.net/Nikto2', badge: 'Scanner' },
        { name: 'Semgrep', desc: 'Analyse statique de code (SAST) multi-langages avec règles de sécurité prêtes à l\'emploi', url: 'https://semgrep.dev', badge: 'SAST' },
        { name: 'Trivy', desc: 'Scanner de vulnérabilités pour conteneurs Docker, dépendances et fichiers IaC', url: 'https://trivy.dev', badge: 'Container' },
        { name: 'Snyk', desc: 'Détection de vulnérabilités dans les dépendances (npm, pip, Maven) avec suggestions de fix automatiques', url: 'https://snyk.io', badge: 'SCA' },
        { name: 'Fail2ban', desc: 'Bloque automatiquement les IP qui tentent des attaques brute force sur SSH, HTTP, etc.', url: 'https://www.fail2ban.org', badge: 'Défense' },
        { name: 'Wazuh', desc: 'SIEM open source : détection d\'intrusion, surveillance d\'intégrité, conformité RGPD/PCI-DSS', url: 'https://wazuh.com', badge: 'SIEM' },
      ],
    },
    {
      icon: 'headphones',
      title: 'Podcasts & Veille Active',
      subtitle: 'Rester informé sans rester devant un écran',
      iconClass: 'text-pink-400',
      links: [
        { name: 'No Limit Secu', desc: 'Le podcast français de référence en cybersécurité — interviews d\'experts, actualité et techniques', url: 'https://www.nolimitsecu.fr', badge: 'FR' },
        { name: 'Darknet Diaries', desc: 'Récits immersifs sur des incidents réels : hackers, espionnage, cybercriminalité — en anglais', url: 'https://darknetdiaries.com', badge: 'EN' },
        { name: 'ANSSI — Flux RSS', desc: 'Alertes de sécurité officielles, avis de vulnérabilités et publications CERT-FR', url: 'https://www.cert.ssi.gouv.fr', badge: 'CERT-FR' },
        { name: 'Krebs on Security', desc: 'Blog de Brian Krebs : investigations approfondies sur la cybercriminalité mondiale', url: 'https://krebsonsecurity.com', badge: 'Blog' },
        { name: 'The Hacker News', desc: 'Actualités quotidiennes sur les vulnérabilités, malwares et incidents cyber', url: 'https://thehackernews.com', badge: 'News' },
      ],
    },
  ];

  youtubeGroups = [
    {
      flag: 'FR',
      label: 'Français',
      channels: [
        { name: 'Michel Kartner', desc: 'Cybersécurité et programmation quel que soit le niveau', url: 'https://www.youtube.com/@MichelKartner' },
        { name: 'Guardia — Ecole de Cybersécurité', desc: 'Actualité cyber, interviews d\'experts, conseils de professionnalisation', url: 'https://www.youtube.com/@GuardiaCybersecurite' },
        { name: 'Passion Cyber', desc: 'Gouvernance, certifications (CISSP), pratiques professionnelles', url: 'https://www.youtube.com/@PassionCyber' },
        { name: 'Cybersécurité 360', desc: 'Gouvernance et mise en conformité pour les entreprises', url: 'https://www.youtube.com/@Cybersecurite360' },
      ],
    },
    {
      flag: 'EN',
      label: 'Anglais',
      channels: [
        { name: 'Professor Messer', desc: 'La référence absolue pour les certifications Security+, Network+', url: 'https://www.youtube.com/@professormesser' },
        { name: 'zSecurity', desc: 'Hacking éthique et tests d\'intrusion — très technique et orienté démonstration', url: 'https://www.youtube.com/@zSecurity' },
        { name: 'Google Career Certificates', desc: 'Modules de formation cybersécurité reconnus par l\'industrie', url: 'https://www.youtube.com/@GoogleCareerCertificates' },
        { name: 'SkillsBuild Security', desc: 'Progresser rapidement vers les métiers d\'Ethical Hacker ou d\'analyste', url: 'https://www.youtube.com/@IBMSkillsBuild' },
      ],
    },
  ];

  glossary = [
    { term: 'CVE', def: 'Common Vulnerabilities and Exposures — identifiant unique attribué à chaque vulnérabilité connue (ex : CVE-2024-1234).' },
    { term: 'CVSS', def: 'Common Vulnerability Scoring System — score de 0 à 10 mesurant la gravité d\'une CVE (critique ≥ 9).' },
    { term: 'Zero-Day', def: 'Vulnérabilité inconnue de l\'éditeur et donc sans correctif disponible au moment de son exploitation.' },
    { term: 'Phishing', def: 'Tentative d\'usurpation d\'identité par email ou site web pour voler des identifiants ou des données.' },
    { term: 'Ransomware', def: 'Logiciel malveillant qui chiffre vos fichiers et réclame une rançon pour les déchiffrer.' },
    { term: 'MFA / 2FA', def: 'Multi-Factor Authentication — authentification avec au moins deux facteurs (mot de passe + code SMS/TOTP).' },
    { term: 'SAST', def: 'Static Application Security Testing — analyse du code source à la recherche de failles sans l\'exécuter.' },
    { term: 'DAST', def: 'Dynamic Application Security Testing — test d\'une application en cours d\'exécution pour détecter des vulnérabilités.' },
    { term: 'SCA', def: 'Software Composition Analysis — audit des dépendances tierces pour détecter des composants vulnérables.' },
    { term: 'XSS', def: 'Cross-Site Scripting — injection de scripts malveillants dans une page web vue par d\'autres utilisateurs.' },
    { term: 'SQLi', def: 'SQL Injection — insertion de code SQL dans un formulaire pour manipuler ou exfiltrer la base de données.' },
    { term: 'SSRF', def: 'Server-Side Request Forgery — forcer le serveur à effectuer des requêtes vers des ressources internes.' },
    { term: 'APT', def: 'Advanced Persistent Threat — groupe d\'attaquants sophistiqués (souvent étatiques) opérant sur le long terme.' },
    { term: 'IOC', def: 'Indicator of Compromise — indice technique (IP, hash, domaine) signalant une compromission.' },
    { term: 'WAF', def: 'Web Application Firewall — pare-feu applicatif filtrant les requêtes HTTP malveillantes en amont du serveur.' },
  ];

  orgRows = [
    { section: 'Lab Technique', sectionClass: 'text-cyan-400', target: 'Développeurs / Ops', use: 'Tester le code, vérifier les dépendances, auditer les serveurs' },
    { section: 'Gouvernance', sectionClass: 'text-purple-400', target: 'Managers / DPO', use: 'Se mettre en règle avec le RGPD et suivre les normes ISO/NIST' },
    { section: 'Visualisation', sectionClass: 'text-orange-400', target: 'Tous publics', use: 'Comprendre qui attaque, pourquoi et comment les menaces évoluent' },
    { section: 'Éthique', sectionClass: 'text-green-400', target: 'Tous publics', use: 'Protéger sa vie privée et comprendre ses droits numériques' },
    { section: 'Outils Open Source', sectionClass: 'text-amber-400', target: 'Développeurs / Ops', use: 'Auditer, scanner et surveiller l\'infrastructure sans coût de licence' },
    { section: 'Podcasts & Veille', sectionClass: 'text-pink-400', target: 'Tous profils', use: 'Rester à jour sur les menaces et incidents sans lire d\'articles' },
  ];
}
