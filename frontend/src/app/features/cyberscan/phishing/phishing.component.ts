import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Title, Meta } from '@angular/platform-browser';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { PHISHING_SCENARIOS } from '../services/phishing-scenarios';

export interface PricingTier {
  id: string;
  name: string;
  price: string;
  priceDetail: string;
  highlight: boolean;
  features: string[];
  cta: string;
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface MethodStep {
  step: number;
  title: string;
  description: string;
  icon: string;
}

export const PRICING_TIERS: PricingTier[] = [
  {
    id: 'express',
    name: 'Phishing Express',
    price: '990 €',
    priceDetail: 'HT — one-shot',
    highlight: false,
    features: [
      '1 campagne de simulation',
      "Jusqu'à 50 cibles",
      '2 scénarios au choix',
      'Rapport synthèse sous 24 h',
      'Taux de clic & compromission',
    ],
    cta: 'Démarrer',
  },
  {
    id: 'standard',
    name: 'Phishing Standard',
    price: '1 890 €',
    priceDetail: 'HT — one-shot',
    highlight: true,
    features: [
      '2 campagnes de simulation',
      "Jusqu'à 200 cibles",
      '5 scénarios au choix',
      'Rapport complet + analyse comportementale',
      'Recommandations de formation',
      'Comparaison avant/après',
    ],
    cta: 'Recommandé',
  },
  {
    id: 'premium',
    name: 'Phishing Premium',
    price: '2 990 €',
    priceDetail: 'HT — one-shot',
    highlight: false,
    features: [
      '3 campagnes de simulation',
      "Jusqu'à 500 cibles",
      '10 scénarios personnalisés',
      'Rapport PDF exécutif + slides COMEX',
      'Recommandations de formation ciblées',
      'Scoring par département',
      'Appel de debriefing inclus',
    ],
    cta: 'Démarrer',
  },
];

export const SUBSCRIPTION_TIERS: PricingTier[] = [
  {
    id: 'quarterly',
    name: 'Trimestrielle',
    price: '250 €',
    priceDetail: 'HT / mois',
    highlight: false,
    features: [
      '1 campagne par trimestre',
      "Jusqu'à 100 cibles",
      '3 scénarios rotatifs',
      'Rapport mensuel de tendance',
      'Tableau de bord évolution',
    ],
    cta: "S'abonner",
  },
  {
    id: 'monthly',
    name: 'Mensuelle',
    price: '600 €',
    priceDetail: 'HT / mois',
    highlight: true,
    features: [
      '1 campagne par mois',
      "Jusqu'à 300 cibles",
      '10 scénarios rotatifs',
      'Rapport PDF mensuel',
      'Score de maturité évolutif',
      'Recommandations formations mensuelles',
      'Accès dashboard temps réel',
    ],
    cta: "S'abonner",
  },
];

export const METHOD_STEPS: MethodStep[] = [
  {
    step: 1,
    title: 'Cadrage & Périmètre',
    description:
      "Définition des cibles, des scénarios adaptés à votre secteur et signature d'une convention d'exercice.",
    icon: 'assignment',
  },
  {
    step: 2,
    title: 'Personnalisation des scénarios',
    description:
      'Adaptation des templates aux couleurs de votre entreprise, fournisseurs et outils internes pour maximiser le réalisme.',
    icon: 'tune',
  },
  {
    step: 3,
    title: 'Lancement de la campagne',
    description:
      'Envoi progressif et discret aux cibles via une infrastructure dédiée (domaine lookalike, serveur isolé).',
    icon: 'send',
  },
  {
    step: 4,
    title: 'Collecte des données',
    description:
      "Suivi en temps réel des taux d'ouverture, de clic, de soumission de formulaire et de téléchargement.",
    icon: 'analytics',
  },
  {
    step: 5,
    title: 'Sensibilisation immédiate',
    description:
      "Affichage d'une page éducative aux collaborateurs ayant cliqué pour une prise de conscience immédiate.",
    icon: 'school',
  },
  {
    step: 6,
    title: 'Rapport & Recommandations',
    description:
      "Livraison d'un rapport détaillé avec taux de compromission, analyse par profil et plan d'actions priorisé.",
    icon: 'description',
  },
];

export const FAQ_ITEMS: FaqItem[] = [
  {
    question: 'Est-ce légal de simuler des attaques phishing sur mes employés ?',
    answer:
      "Oui, sous réserve d'une convention d'exercice signée entre l'entreprise et Rocher Cybersécurité. Une information générale peut être communiquée aux collaborateurs (sans révéler la date). Les données collectées sont strictement anonymisées dans les rapports. Nous fournissons un modèle de convention conforme au RGPD.",
  },
  {
    question: "Les employés sont-ils prévenus à l'avance ?",
    answer:
      "Non — l'efficacité d'une simulation repose sur l'effet de surprise. En revanche, l'entreprise est informée du cadre légal et peut décider de communiquer sur l'existence d'un programme de sensibilisation sans révéler les dates ni les scénarios.",
  },
  {
    question: 'Que se passe-t-il si un employé clique sur le lien de phishing ?',
    answer:
      "Aucune donnée réelle n'est capturée. L'employé est redirigé vers une page de sensibilisation expliquant qu'il vient de participer à un exercice et donnant 3 conseils clés pour reconnaître un vrai phishing.",
  },
  {
    question: 'La simulation peut-elle impacter notre infrastructure ?',
    answer:
      "Non. L'infrastructure est entièrement isolée (domaine dédié, serveur séparé). Aucun code malveillant réel n'est utilisé. Les simulations de pièces jointes sont des fichiers inoffensifs qui mesurent uniquement l'ouverture.",
  },
  {
    question: 'Combien de temps dure une campagne ?',
    answer:
      "Une campagne dure généralement 1 à 2 semaines pour garantir que tous les collaborateurs aient l'opportunité de recevoir l'email, quelle que soit leur présence. Le rapport est livré sous 24 à 72 h après la fin de la campagne.",
  },
  {
    question: 'Pouvez-vous cibler des profils spécifiques (direction, comptabilité) ?',
    answer:
      "Oui. La segmentation par département, niveau hiérarchique ou profil de risque est disponible à partir de l'offre Standard. Cela permet d'identifier les populations les plus vulnérables et de prioriser les formations.",
  },
];

export const USE_CASES = [
  {
    icon: 'warning_amber',
    title: 'Post-incident',
    subtitle: 'PME victime de phishing réel',
    description:
      "Une PME de 80 personnes a subi une attaque par phishing (compromission messagerie). Après l'incident, la direction a voulu mesurer le niveau de vulnérabilité réel des équipes et former les profils les plus à risque.",
    result:
      '34 % des employés ont cliqué lors de la première campagne → formation ciblée → 8 % lors de la seconde.',
    color: 'red',
  },
  {
    icon: 'gavel',
    title: 'Conformité NIS2',
    subtitle: 'ETI dans le secteur énergie',
    description:
      "Entité essentielle soumise à NIS2, le RSSI devait justifier d'un programme de sensibilisation documenté. Les simulations phishing constituent une preuve d'exercice concrète pour les auditeurs.",
    result:
      "Programme trimestriel intégré à la feuille de route NIS2, rapport fourni à l'ANSSI sur demande.",
    color: 'blue',
  },
  {
    icon: 'balance',
    title: 'Cabinet Juridique',
    subtitle: 'Données clients ultra-sensibles',
    description:
      "Un cabinet d'avocats manipulant des données confidentielles souhaitait tester la résistance de ses 25 collaborateurs face aux tentatives d'ingénierie sociale ciblant les dossiers clients.",
    result:
      'Identification de 3 profils à haut risque → formation individuelle → zéro incident sur les 12 mois suivants.',
    color: 'purple',
  },
];

@Component({
  standalone: true,
  selector: 'app-phishing',
  imports: [RouterLink, MatButtonModule, MatIconModule, NavButtonsComponent],
  templateUrl: './phishing.component.html',
})
export class PhishingComponent implements OnInit {
  private title = inject(Title);
  private meta = inject(Meta);

  readonly scenarios = PHISHING_SCENARIOS;
  readonly pricingTiers = PRICING_TIERS;
  readonly subscriptionTiers = SUBSCRIPTION_TIERS;
  readonly methodSteps = METHOD_STEPS;
  readonly faqItems = FAQ_ITEMS;
  readonly useCases = USE_CASES;

  openFaqIndex = signal<number | null>(null);

  ngOnInit() {
    this.title.setTitle(
      'Simulation de Phishing pour PME — Test et Sensibilisation | Rocher Cybersécurité'
    );
    this.meta.updateTag({
      name: 'description',
      content:
        'Testez la résistance de vos équipes au phishing avec des campagnes réalistes. Rapports détaillés, conformité NIS2, à partir de 990 € HT.',
    });
  }

  toggleFaq(index: number): void {
    this.openFaqIndex.update(i => (i === index ? null : index));
  }

  difficultyColor(difficulty: string): string {
    switch (difficulty) {
      case 'Facile':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'Moyen':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      case 'Difficile':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      default:
        return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
    }
  }

  useCaseColor(color: string): { border: string; icon: string; badge: string } {
    switch (color) {
      case 'red':
        return {
          border: 'border-red-500/30',
          icon: 'text-red-400 bg-red-500/10',
          badge: 'bg-red-500/10 text-red-300 border-red-500/30',
        };
      case 'blue':
        return {
          border: 'border-blue-500/30',
          icon: 'text-blue-400 bg-blue-500/10',
          badge: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
        };
      case 'purple':
        return {
          border: 'border-purple-500/30',
          icon: 'text-purple-400 bg-purple-500/10',
          badge: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
        };
      default:
        return {
          border: 'border-gray-700',
          icon: 'text-gray-400 bg-gray-800',
          badge: 'bg-gray-700 text-gray-300 border-gray-600',
        };
    }
  }
}
