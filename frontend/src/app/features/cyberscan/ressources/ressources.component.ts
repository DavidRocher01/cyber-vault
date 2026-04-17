import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { Title, Meta } from '@angular/platform-browser';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    selector: 'app-ressources',
    imports: [RouterLink, MatIconModule, MatButtonModule, NavButtonsComponent],
    templateUrl: './ressources.component.html'
})
export class RessourcesComponent {
  private titleService = inject(Title);
  private meta = inject(Meta);

  constructor() {
    this.titleService.setTitle('Ressources cybersécurité — CyberScan');
    this.meta.updateTag({ name: 'description', content: 'Outils, plateformes et chaînes YouTube sélectionnés pour approfondir vos connaissances en cybersécurité : audits, gouvernance, RGPD, CTF.' });
    this.meta.updateTag({ property: 'og:title', content: 'Ressources cybersécurité — CyberScan' });
    this.meta.updateTag({ property: 'og:description', content: 'Outils, plateformes et chaînes YouTube pour approfondir vos connaissances en cybersécurité.' });
    this.meta.updateTag({ property: 'og:url', content: 'https://cyberscanapp.com/cyberscan/ressources' });
    this.meta.updateTag({ property: 'og:title', content: 'Ressources cybersécurité — CyberScan' });
    this.meta.updateTag({ property: 'og:description', content: 'Outils, plateformes et chaînes YouTube pour la cybersécurité.' });
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
        { name: 'Root-Me', desc: 'Apprendre le hacking éthique via des exercices progressifs et des CTF', url: 'https://www.root-me.org', badge: 'CTF' },
        { name: 'TryHackMe', desc: 'Parcours guidés pour la cybersécurité offensive et défensive', url: 'https://tryhackme.com', badge: 'CTF' },
        { name: 'Google Security Blog', desc: 'Vision de pointe sur la sécurisation des infrastructures à grande échelle', url: 'https://security.googleblog.com', badge: 'Veille' },
      ],
    },
    {
      icon: 'gavel',
      title: 'Gouvernance & Conformité',
      subtitle: 'Pour les managers, DPO et responsables RSSI',
      iconClass: 'text-purple-400',
      links: [
        { name: 'ANSSI — Cyber-Guide', desc: 'Fiches pratiques pour mettre en place une hygiène informatique en entreprise', url: 'https://www.ssi.gouv.fr/guide/la-cybersecurite-pour-les-tpe-pme-en-12-questions/', badge: 'ANSSI' },
        { name: 'CNIL — Sécurité des données', desc: 'Guide indispensable pour lier technique et obligations légales (RGPD)', url: 'https://www.cnil.fr/fr/securite-informatique', badge: 'RGPD' },
        { name: 'Cybermalveillance.gouv.fr', desc: 'Supports prêts à l\'emploi pour sensibiliser vos collaborateurs', url: 'https://www.cybermalveillance.gouv.fr', badge: 'Sensibilisation' },
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

  orgRows = [
    { section: 'Lab Technique', sectionClass: 'text-cyan-400', target: 'Développeurs / Ops', use: 'Tester le code, vérifier les dépendances, auditer les serveurs' },
    { section: 'Gouvernance', sectionClass: 'text-purple-400', target: 'Managers / DPO', use: 'Se mettre en règle avec le RGPD et suivre les normes ISO/NIST' },
    { section: 'Visualisation', sectionClass: 'text-orange-400', target: 'Tous publics', use: 'Comprendre qui attaque, pourquoi et comment les menaces évoluent' },
    { section: 'Éthique', sectionClass: 'text-green-400', target: 'Tous publics', use: 'Protéger sa vie privée et comprendre ses droits numériques' },
  ];
}
