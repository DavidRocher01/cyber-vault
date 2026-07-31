import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import {
  NB_MODULES,
  DUREE_TOTALE_MINUTES,
  PARCOURS,
} from '../../../shared/awareness-catalog.generated';
import {
  PLANS,
  MIN_CLIENTS_PARTENAIRE,
  REMISE_PARTENAIRE,
  prixPartenaire,
} from '../../../shared/awareness-plans';

@Component({
  standalone: true,
  selector: 'app-awareness-pricing',
  imports: [RouterLink, MatButtonModule, MatIconModule, NavButtonsComponent],
  template: `
    <app-nav-buttons />

    <div class="min-h-screen bg-gray-950 text-white p-4 md:p-12">
      <div class="max-w-5xl mx-auto">
        <!-- Header -->
        <div class="text-center mb-12">
          <div
            class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-cyan-600/30 bg-cyan-500/5 text-cyan-400 text-xs font-semibold mb-4"
          >
            <mat-icon class="!text-[0.9rem] !w-[0.9rem] !h-[0.9rem]">school</mat-icon>
            Sensibilisation NIS2
          </div>
          <h1
            class="text-3xl md:text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent mb-3"
          >
            Formez vos équipes à la cybersécurité
          </h1>
          <p class="text-gray-400 text-lg max-w-2xl mx-auto">
            {{ nbModules }} modules e-learning NIS2 Article 21, attestations vérifiables et tableau
            de bord de conformité. Simple, traçable, prêt en 48h.
          </p>
          <div
            class="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-full border border-amber-600/30 bg-amber-500/5 text-amber-400 text-sm"
          >
            <mat-icon class="!text-[1rem] !w-[1rem] !h-[1rem]">info</mat-icon>
            Tarification sur devis — les prix ci-dessous sont indicatifs.
            <a
              routerLink="/contact"
              [queryParams]="{ subject: 'sensibilisation-nis2' }"
              class="underline hover:text-amber-300"
              >Nous contacter</a
            >
          </div>
        </div>

        <!-- Plans grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
          @for (plan of plans; track plan.id) {
            <div
              class="rounded-xl border flex flex-col transition-all"
              [class]="
                plan.featured
                  ? 'border-cyan-500/50 bg-gray-900 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500/20'
                  : 'border-gray-800 bg-gray-900 hover:border-gray-700'
              "
            >
              <!-- Plan header -->
              <div class="p-5 border-b border-gray-800">
                <div class="flex items-start justify-between mb-3">
                  <span class="text-white font-bold text-lg">{{ plan.name }}</span>
                  @if (plan.badge) {
                    <span
                      class="text-[0.65rem] font-bold px-1.5 py-0.5 rounded-full"
                      [class]="
                        plan.featured
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-600/30'
                          : 'bg-gray-700 text-gray-300 border border-gray-600'
                      "
                    >
                      {{ plan.badge }}
                    </span>
                  }
                </div>
                <div class="mb-1">
                  <span class="text-3xl font-bold text-white">{{ plan.price }}€</span>
                  <span class="text-gray-500 text-sm"> / {{ plan.period }}</span>
                </div>
                <p class="text-gray-400 text-xs">
                  {{
                    plan.maxLearners
                      ? "Jusqu'à " + plan.maxLearners + ' learners'
                      : 'Learners illimités'
                  }}
                </p>
              </div>

              <!-- Features -->
              <div class="p-5 flex-1">
                <ul class="flex flex-col gap-2.5">
                  @for (feature of plan.features; track feature) {
                    <li class="flex items-start gap-2 text-sm">
                      <mat-icon
                        class="text-cyan-400 !text-[1rem] !w-[1rem] !h-[1rem] shrink-0 mt-0.5"
                        >check</mat-icon
                      >
                      <span class="text-gray-300">{{ feature }}</span>
                    </li>
                  }
                </ul>
              </div>

              <!-- CTA -->
              <div class="p-5 pt-0">
                <a
                  routerLink="/contact"
                  [queryParams]="{ subject: 'sensibilisation-nis2' }"
                  mat-flat-button
                  class="w-full !rounded-xl !text-sm"
                  [class]="
                    plan.featured
                      ? '!bg-cyan-600 hover:!bg-cyan-500 !text-white'
                      : '!bg-gray-800 hover:!bg-gray-700 !text-gray-200'
                  "
                >
                  Demander un devis {{ plan.name }}
                </a>
              </div>
            </div>
          }
        </div>

        <!-- Offre partenaire : consultants RSSI qui pilotent plusieurs clients.
             Prix DERIVES du barreme direct (meme logique de taille), pour qu'un
             gros compte ne passe pas par un consultant juste pour changer de
             barreme. -->
        <div class="rounded-xl border border-amber-700/40 bg-amber-900/10 p-6 mb-12">
          <div class="flex flex-wrap items-center gap-3 mb-2">
            <mat-icon class="text-amber-400 !text-[1.2rem] !w-[1.2rem] !h-[1.2rem]"
              >handshake</mat-icon
            >
            <h2 class="text-white font-semibold">Vous êtes consultant RSSI ?</h2>
            <span
              class="text-[0.7rem] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-600/30"
            >
              -{{ remisePartenairePct }} %
            </span>
          </div>
          <p class="text-gray-400 text-sm mb-5">
            Formez les équipes de vos clients depuis un seul compte. Tarif partenaire à partir de
            {{ minClientsPartenaire }} organisations clientes, facturé par client selon sa taille.
          </p>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            @for (plan of plans; track plan.id) {
              <div class="rounded-lg border border-gray-800 bg-gray-900 p-4">
                <p class="text-gray-500 text-xs mb-1">
                  {{ plan.maxLearners ? "jusqu'à " + plan.maxLearners : 'illimité' }} apprenants
                </p>
                <p class="text-amber-400 text-xl font-bold">{{ prixPartenaire(plan) }}€</p>
                <p class="text-gray-600 text-xs line-through">{{ plan.price }}€ en direct</p>
              </div>
            }
          </div>
          <a
            routerLink="/contact"
            [queryParams]="{ subject: 'partenaire-sensibilisation' }"
            mat-flat-button
            class="!bg-amber-600 hover:!bg-amber-500 !text-white !rounded-xl !text-sm"
          >
            Devenir partenaire
          </a>
        </div>

        <!-- Feature comparison -->
        <div class="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden mb-12">
          <div class="p-6 border-b border-gray-800">
            <h2 class="text-white font-semibold">Toutes les fonctionnalités incluses</h2>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 p-6">
            @for (group of featureGroups; track group.title) {
              <div>
                <div class="flex items-center gap-2 mb-3">
                  <mat-icon class="text-cyan-400 !text-[1rem] !w-[1rem] !h-[1rem]">{{
                    group.icon
                  }}</mat-icon>
                  <span class="text-white font-medium text-sm">{{ group.title }}</span>
                </div>
                <ul class="flex flex-col gap-1.5">
                  @for (item of group.items; track item) {
                    <li class="text-gray-400 text-xs flex items-center gap-1.5">
                      <mat-icon class="text-gray-600 !text-[0.75rem] !w-[0.75rem] !h-[0.75rem]"
                        >fiber_manual_record</mat-icon
                      >
                      {{ item }}
                    </li>
                  }
                </ul>
              </div>
            }
          </div>
        </div>

        <!-- FAQ / Guarantees -->
        <div class="text-center">
          <p class="text-gray-400 text-sm mb-4">
            Tous les plans incluent un essai gratuit de 14 jours · Sans engagement · Résiliable à
            tout moment
          </p>
          <a
            routerLink="/contact"
            mat-stroked-button
            class="!rounded-xl !border-gray-700 !text-gray-300 !text-sm"
          >
            Besoin d'un devis sur mesure ?
          </a>
        </div>
      </div>
    </div>
  `,
})
export class AwarenessPricingComponent {
  readonly plans = PLANS;
  /** Tarif partenaire : DERIVE du barreme direct, jamais recopie. */
  readonly prixPartenaire = prixPartenaire;
  readonly remisePartenairePct = Math.round(REMISE_PARTENAIRE * 100);
  readonly minClientsPartenaire = MIN_CLIENTS_PARTENAIRE;
  /** Catalogue derive de content/fr/ — jamais recopie a la main. */
  readonly parcours = PARCOURS;
  readonly nbModules = NB_MODULES;

  readonly featureGroups = [
    {
      icon: 'menu_book',
      title: 'Formation',
      items: [
        `${NB_MODULES} modules NIS2 Article 21`,
        'Quiz adaptatifs (3 tentatives)',
        'Progression séquentielle',
        `Parcours complet ~${DUREE_TOTALE_MINUTES} min`,
        'Contenu mis à jour régulièrement',
      ],
    },
    {
      icon: 'verified',
      title: 'Attestations',
      items: [
        'PDF généré automatiquement',
        'QR code de vérification',
        'Signature SHA-256 infalsifiable',
        'Validité 12 mois',
        'Page de vérification publique',
      ],
    },
    {
      icon: 'bar_chart',
      title: 'Pilotage',
      items: [
        'Dashboard de complétion par org',
        'Score de conformité NIS2',
        'Alertes at-risk learners',
        'Rapport PDF téléchargeable',
        'Export données CSV',
      ],
    },
  ];
}
