import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { Title, Meta } from '@angular/platform-browser';
import { DOCUMENT } from '@angular/common';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
    standalone: true,
    selector: 'app-bonnes-pratiques',
    imports: [RouterLink, MatIconModule, MatButtonModule, NavButtonsComponent],
    templateUrl: './bonnes-pratiques.component.html'
})
export class BonnesPratiquesComponent {
  private titleService = inject(Title);
  private meta = inject(Meta);
  private doc = inject(DOCUMENT);

  constructor() {
    this.titleService.setTitle('Bonnes pratiques cybersécurité — CyberScan');
    this.meta.updateTag({ name: 'description', content: 'Conseils pratiques pour renforcer votre sécurité : mots de passe, MFA, phishing, Wi-Fi public, sécurité physique. Accessibles à tous.' });
    this.meta.updateTag({ property: 'og:title', content: 'Bonnes pratiques cybersécurité — CyberScan' });
    this.meta.updateTag({ property: 'og:description', content: 'Mots de passe, MFA, phishing, Wi-Fi — les fondamentaux de la cybersécurité.' });
    this.meta.updateTag({ property: 'og:url', content: 'https://cyberscanapp.com/cyberscan/bonnes-pratiques' });
    this.meta.updateTag({ property: 'og:type', content: 'website' });
    this._setCanonical('https://cyberscanapp.com/cyberscan/bonnes-pratiques');
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

  sections = [
    {
      icon: 'vpn_key',
      title: 'Gestion des Identités',
      badge: 'Mots de passe & MFA',
      badgeClass: 'bg-cyan-900/50 text-cyan-400 border border-cyan-700',
      iconClass: 'text-cyan-400',
      items: [
        {
          icon: 'lock',
          title: 'Utiliser un gestionnaire de mots de passe',
          desc: 'Des outils comme Bitwarden ou KeePassXC permettent d\'avoir des mots de passe uniques et complexes sans effort de mémorisation. Un seul mot de passe maître fort protège tous les autres.',
          link: 'https://bitwarden.com',
          linkLabel: 'Bitwarden — gratuit et open source',
        },
        {
          icon: 'smartphone',
          title: 'Activer la Double Authentification (MFA/2FA)',
          desc: 'Même si un mot de passe est volé, l\'accès reste protégé grâce au second facteur. La plupart des services importants (email, banque, cloud) le proposent.',
          link: 'https://2fa.directory/fr/',
          linkLabel: '2FA Directory — liste des services compatibles',
        },
      ],
    },
    {
      icon: 'phishing',
      title: 'Détecter le Phishing',
      badge: 'Ingénierie Sociale',
      badgeClass: 'bg-yellow-900/50 text-yellow-400 border border-yellow-700',
      iconClass: 'text-yellow-400',
      items: [
        {
          icon: 'mouse',
          title: 'Vérifier avant de cliquer',
          desc: 'Survolez un lien avec la souris pour voir l\'URL réelle avant de cliquer. Vérifiez que le domaine correspond bien à l\'expéditeur (ex: "secure-paypal.xyz" n\'est pas PayPal).',
          link: 'https://www.phishtank.com',
          linkLabel: 'PhishTank — base de données des sites de phishing signalés',
        },
        {
          icon: 'call',
          title: 'Le test du Canal Secondaire',
          desc: 'Si une demande est suspecte (virement urgent, changement de RIB, accès exceptionnel), confirmez toujours par un autre moyen (appel direct) sans utiliser les coordonnées fournies dans l\'email.',
          link: null,
          linkLabel: null,
        },
      ],
    },
    {
      icon: 'screen_lock_portrait',
      title: 'Sécurité Physique',
      badge: 'Environnement & Bureau',
      badgeClass: 'bg-purple-900/50 text-purple-400 border border-purple-700',
      iconClass: 'text-purple-400',
      items: [
        {
          icon: 'lock_clock',
          title: 'Verrouiller son écran automatiquement',
          desc: 'Prenez l\'habitude de verrouiller votre écran dès que vous quittez votre poste, même pour 30 secondes. Raccourci Windows : Win+L, Mac : Cmd+Ctrl+Q.',
          link: null,
          linkLabel: null,
        },
        {
          icon: 'usb',
          title: 'Méfiance vis-à-vis des périphériques inconnus',
          desc: 'Ne branchez jamais une clé USB trouvée "par hasard". Une clé piégée (Rubber Ducky) peut compromettre votre poste en quelques secondes et exécuter des commandes à votre insu.',
          link: null,
          linkLabel: null,
        },
        {
          icon: 'visibility_off',
          title: 'Filtres de confidentialité',
          desc: 'Indispensables pour le travail en espaces publics ou dans les transports. Ils empêchent le "shoulder surfing" (lecture par-dessus l\'épaule).',
          link: null,
          linkLabel: null,
        },
      ],
    },
    {
      icon: 'wifi',
      title: 'Protection en Mobilité',
      badge: 'Télétravail & Déplacements',
      badgeClass: 'bg-green-900/50 text-green-400 border border-green-700',
      iconClass: 'text-green-400',
      items: [
        {
          icon: 'wifi_off',
          title: 'Éviter les Wi-Fi publics ouverts',
          desc: 'Préférez le partage de connexion mobile (4G/5G) ou un VPN de confiance. Ne vous connectez jamais à votre banque ou à des outils professionnels depuis un Wi-Fi public.',
          link: 'https://www.privacyguides.org/fr/vpn/',
          linkLabel: 'Privacy Guides — recommandations VPN',
        },
        {
          icon: 'desk',
          title: 'Le "Clean Desk"',
          desc: 'Ne laissez pas de post-it avec des codes d\'accès ni de documents sensibles visibles sur votre bureau physique. Cela vaut aussi en télétravail lors de visioconférences.',
          link: null,
          linkLabel: null,
        },
      ],
    },
    {
      icon: 'code',
      title: 'Sécurité CI/CD & DevSecOps',
      badge: 'Développeurs & Ops',
      badgeClass: 'bg-cyan-900/50 text-cyan-400 border border-cyan-700',
      iconClass: 'text-cyan-400',
      items: [
        {
          icon: 'key_off',
          title: 'Ne jamais committer de secrets dans le code',
          desc: 'Clés API, mots de passe, tokens — aucun secret ne doit figurer dans un dépôt Git, même privé. Utilisez des variables d\'environnement et des outils comme detect-secrets ou GitGuardian pour scanner automatiquement vos commits.',
          link: 'https://github.com/Yelp/detect-secrets',
          linkLabel: 'detect-secrets — scanner de secrets open source',
        },
        {
          icon: 'inventory_2',
          title: 'Auditer les dépendances tiers (SCA)',
          desc: 'Chaque dépendance npm ou pip est une surface d\'attaque potentielle. Intégrez un outil SCA (Snyk, pip-audit, npm audit) dans votre pipeline CI pour détecter les CVE avant la mise en production.',
          link: 'https://snyk.io',
          linkLabel: 'Snyk — audit de dépendances',
        },
        {
          icon: 'lock',
          title: 'Sécuriser les secrets CI/CD',
          desc: 'Stockez vos secrets GitHub Actions, GitLab CI ou autres dans les vaults chiffrés de la plateforme, jamais en clair dans les fichiers de workflow. Limitez leur durée de vie et leur périmètre d\'accès (least privilege).',
          link: null,
          linkLabel: null,
        },
        {
          icon: 'policy',
          title: 'Activer la revue de code (Pull Request)',
          desc: 'Aucun code ne devrait atteindre la production sans avoir été relu par au moins un autre développeur. La revue de code est l\'une des mesures les plus efficaces contre les injections et les régressions de sécurité.',
          link: null,
          linkLabel: null,
        },
      ],
    },
    {
      icon: 'cloud',
      title: 'Cloud & Infrastructure',
      badge: 'AWS / GCP / Azure',
      badgeClass: 'bg-orange-900/50 text-orange-400 border border-orange-700',
      iconClass: 'text-orange-400',
      items: [
        {
          icon: 'manage_accounts',
          title: 'Principe du moindre privilège (Least Privilege)',
          desc: 'Chaque compte, rôle IAM ou service ne doit avoir accès qu\'à ce dont il a strictement besoin. Auditez régulièrement vos permissions cloud et supprimez les droits inutilisés — ils représentent la première source de compromission cloud.',
          link: null,
          linkLabel: null,
        },
        {
          icon: 'folder_off',
          title: 'Vérifier la visibilité de vos buckets S3 / GCS',
          desc: 'Des buckets S3 publics par erreur ont exposé des millions de données sensibles. Activez l\'option "Block Public Access" par défaut et auditez vos ACL régulièrement. Jamais de données clients dans un bucket public.',
          link: null,
          linkLabel: null,
        },
        {
          icon: 'router',
          title: 'Réduire la surface d\'exposition réseau',
          desc: 'Fermez tous les ports inutiles dans vos Security Groups. SSH (22) et RDP (3389) ne doivent jamais être ouverts à 0.0.0.0/0. Utilisez un bastion ou un VPN pour les accès d\'administration.',
          link: null,
          linkLabel: null,
        },
        {
          icon: 'receipt_long',
          title: 'Activer les logs et alertes cloud',
          desc: 'CloudTrail (AWS), Cloud Audit Logs (GCP) — activez l\'enregistrement de toutes les actions sur vos ressources cloud. Configurez des alertes pour les actions anormales : création d\'utilisateur IAM, suppression de logs, ouverture de port.',
          link: null,
          linkLabel: null,
        },
      ],
    },
    {
      icon: 'system_update',
      title: 'Mises à Jour & Gestion des Patchs',
      badge: 'Fondamental',
      badgeClass: 'bg-red-900/50 text-red-400 border border-red-700',
      iconClass: 'text-red-400',
      items: [
        {
          icon: 'update',
          title: 'Appliquer les correctifs dès leur publication',
          desc: '60 % des violations exploitent des vulnérabilités pour lesquelles un patch existait. Configurez les mises à jour automatiques sur vos systèmes d\'exploitation et planifiez une fenêtre de maintenance hebdomadaire pour vos serveurs.',
          link: null,
          linkLabel: null,
        },
        {
          icon: 'track_changes',
          title: 'Surveiller les CVE de vos composants',
          desc: 'Abonnez-vous aux alertes CERT-FR et aux flux de sécurité de vos fournisseurs. Pour vos applications, un outil SCA dans le CI détectera automatiquement les nouvelles CVE publiées sur vos dépendances.',
          link: 'https://www.cert.ssi.gouv.fr',
          linkLabel: 'CERT-FR — alertes de sécurité officielles',
        },
        {
          icon: 'verified',
          title: 'Tester les patchs en staging avant prod',
          desc: 'Un patch peut casser une fonctionnalité ou introduire une régression. Toujours valider en environnement de pré-production avant de déployer sur les serveurs critiques.',
          link: null,
          linkLabel: null,
        },
      ],
    },
  ];

  tableRows = [
    { risk: 'Accès', bad: '"123456" ou le même mot de passe partout', good: 'Un coffre-fort numérique (Bitwarden)' },
    { risk: 'Email', bad: 'Cliquer par peur ou par urgence', good: 'Analyser l\'expéditeur et survoler le lien' },
    { risk: 'Bureau', bad: 'Écran allumé pendant la pause café', good: 'Raccourci de verrouillage (Win+L)' },
    { risk: 'Wi-Fi public', bad: 'Connexion au Wi-Fi "Gare_Gratuit"', good: 'Utilisation de la 4G/5G ou d\'un VPN' },
    { risk: 'USB', bad: 'Brancher une clé trouvée par terre', good: 'Ne jamais connecter un périphérique inconnu' },
    { risk: 'Code source', bad: 'Token API hardcodé dans le dépôt Git', good: 'Variable d\'environnement + detect-secrets en CI' },
    { risk: 'Cloud IAM', bad: 'Compte admin avec droits wildcard (*)', good: 'Rôle IAM restreint au strict nécessaire' },
    { risk: 'S3 / Stockage', bad: 'Bucket public "par défaut"', good: 'Block Public Access activé + audit ACL régulier' },
    { risk: 'Patchs', bad: 'Mettre à jour "quand on a le temps"', good: 'Fenêtre de maintenance hebdomadaire + alertes CVE' },
    { risk: 'CI/CD', bad: 'Secrets en clair dans le fichier workflow', good: 'Vault CI chiffré + least privilege sur les tokens' },
  ];
}
