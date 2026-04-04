import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { Title, Meta } from '@angular/platform-browser';

@Component({
  selector: 'app-bonnes-pratiques',
  standalone: true,
  imports: [RouterLink, MatIconModule, MatButtonModule],
  templateUrl: './bonnes-pratiques.component.html',
})
export class BonnesPratiquesComponent {
  private titleService = inject(Title);
  private meta = inject(Meta);

  constructor() {
    this.titleService.setTitle('Bonnes pratiques cybersécurité — CyberScan');
    this.meta.updateTag({ name: 'description', content: 'Conseils pratiques pour renforcer votre sécurité : mots de passe, MFA, phishing, Wi-Fi public, sécurité physique. Accessibles à tous.' });
    this.meta.updateTag({ property: 'og:title', content: 'Bonnes pratiques cybersécurité — CyberScan' });
    this.meta.updateTag({ property: 'og:description', content: 'Mots de passe, MFA, phishing, Wi-Fi — les fondamentaux de la cybersécurité.' });
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
  ];

  tableRows = [
    { risk: 'Accès', bad: '"123456" ou le même mot de passe partout', good: 'Un coffre-fort numérique (Bitwarden)' },
    { risk: 'Email', bad: 'Cliquer par peur ou par urgence', good: 'Analyser l\'expéditeur et survoler le lien' },
    { risk: 'Bureau', bad: 'Écran allumé pendant la pause café', good: 'Raccourci de verrouillage (Win+L)' },
    { risk: 'Wi-Fi public', bad: 'Connexion au Wi-Fi "Gare_Gratuit"', good: 'Utilisation de la 4G/5G ou d\'un VPN' },
    { risk: 'USB', bad: 'Brancher une clé trouvée par terre', good: 'Ne jamais connecter un périphérique inconnu' },
  ];
}
