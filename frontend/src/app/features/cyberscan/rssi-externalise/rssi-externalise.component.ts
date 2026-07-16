import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { Title, Meta } from '@angular/platform-browser';

import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-rssi-externalise',
  imports: [RouterLink, MatIconModule, NavButtonsComponent],
  templateUrl: './rssi-externalise.component.html',
})
export class RssiExternaliseComponent {
  private title = inject(Title);
  private meta = inject(Meta);

  constructor() {
    this.title.setTitle('RSSI externalisé — votre RSSI à temps partagé | Rocher Cybersécurité');
    this.meta.updateTag({
      name: 'description',
      content:
        'RSSI externalisé pour PME : un expert cybersécurité qui pilote votre conformité NIS2 et ' +
        'votre sécurité au quotidien, sans le coût d’un temps plein. Diagnostic gratuit.',
    });
  }

  readonly pains = [
    { icon: 'gavel', text: 'NIS2 vous concerne — mais vous ne savez pas par où commencer.' },
    { icon: 'person_off', text: 'Vous n’avez pas de RSSI, et vos équipes IT sont déjà saturées.' },
    {
      icon: 'payments',
      text: 'Un RSSI à temps plein coûte 80–110 k€/an — hors de portée pour une PME.',
    },
  ];

  readonly pillars = [
    {
      icon: 'policy',
      title: 'Audit & conformité',
      desc: 'Cartographie du SI, diagnostic NIS2 & ISO 27001, analyse des risques, score de maturité.',
    },
    {
      icon: 'checklist',
      title: 'Plan d’action suivi',
      desc: 'Une feuille de route priorisée (responsables, échéances) tenue à jour à chaque intervention.',
    },
    {
      icon: 'event_available',
      title: 'Visites régulières',
      desc: 'Des points périodiques, à distance ou sur site, pour avancer concrètement.',
    },
    {
      icon: 'insights',
      title: 'Comité de pilotage',
      desc: 'Un reporting trimestriel et un tableau de bord de conformité, présentables à la direction.',
    },
  ];

  readonly steps = [
    {
      step: 1,
      icon: 'radar',
      title: 'Diagnostic',
      desc: 'Scan + évaluation NIS2/ISO : on mesure votre exposition.',
    },
    {
      step: 2,
      icon: 'route',
      title: 'Feuille de route',
      desc: 'Un plan d’action priorisé et réaliste.',
    },
    {
      step: 3,
      icon: 'sync',
      title: 'Suivi mensuel',
      desc: 'On avance ensemble, on met à jour, on surveille.',
    },
    {
      step: 4,
      icon: 'summarize',
      title: 'Comité trimestriel',
      desc: 'On présente les résultats et la suite.',
    },
  ];

  readonly formulas = [
    {
      name: 'Starter',
      cadence: '~1 jour / mois',
      target: 'TPE/PME qui veulent être « en règle NIS2 ».',
      highlight: false,
      includes: [
        'Audit initial + roadmap NIS2',
        'Surveillance continue (scan + dark web)',
        'Point mensuel + reporting trimestriel',
        'Veille réglementaire + hotline conseil',
      ],
    },
    {
      name: 'Standard',
      cadence: '~2 jours / mois',
      target: 'PME en scope NIS2 avec des enjeux clients.',
      highlight: true,
      includes: [
        'Tout le Starter',
        'Politique de sécurité (PSSI) + procédures',
        'Sensibilisation des équipes',
        'Réponse aux questionnaires sécurité clients',
        'Comité de pilotage sur site',
      ],
    },
    {
      name: 'Renforcé',
      cadence: '~4 jours / mois',
      target: 'ETI / secteur régulé aux exigences fortes.',
      highlight: false,
      includes: [
        'Tout le Standard',
        'PCA/PRA + gestion d’incident (astreinte conseil)',
        'Accompagnement à la certification ISO 27001',
        'Pilotage de vos projets sécurité',
      ],
    },
  ];

  readonly whyUs = [
    {
      icon: 'flag',
      title: 'Souveraineté française',
      desc: 'Vos données hébergées en France (AWS Paris), aucun transfert hors UE.',
    },
    {
      icon: 'dashboard_customize',
      title: 'Une plateforme, pas un tableur',
      desc: 'Audit, plan d’action, surveillance et rapports centralisés dans un outil professionnel.',
    },
    {
      icon: 'handshake',
      title: 'Humain + logiciel',
      desc: 'Un vrai expert qui prend la responsabilité, épaulé par la technologie.',
    },
  ];

  readonly faqs = [
    {
      q: 'Concrètement, vous faites quoi chaque mois ?',
      a: 'On tient votre plan d’action à jour, on surveille votre exposition, on vous conseille sur les décisions de sécurité, on prépare vos comités et vos preuves de conformité.',
    },
    {
      q: 'Est-ce que ça remplace un RSSI interne ?',
      a: 'Pour une PME qui n’a pas les moyens d’un temps plein, oui : on assure la fonction RSSI à temps partagé. Pour une organisation plus grande, on vient en renfort de l’équipe existante.',
    },
    {
      q: 'Comment démarre-t-on ?',
      a: 'Par un diagnostic gratuit de 30 minutes : on évalue votre situation et votre exposition NIS2, puis on vous propose la formule adaptée.',
    },
    {
      q: 'Quel est l’engagement ?',
      a: 'Les missions sont généralement sur 12 mois renouvelables, avec un point de renouvellement clair. On cadre tout dans une lettre de mission.',
    },
  ];
}
