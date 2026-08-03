import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

import { AdminAuthService } from '../admin-auth.service';

interface LigneSource {
  source: string;
  scans: number;
  inscriptions: number;
  abonnements: number;
  mrr_cents: number;
  taux_conversion: number;
}

interface LignePage {
  page: string;
  scans: number;
  inscriptions: number;
  abonnements: number;
}

interface VueAcquisition {
  fenetre: string;
  jours: number;
  tunnel: Record<string, number>;
  sources: LigneSource[];
  pages: LignePage[];
  mrr_signe_cents: number;
  mrr_actif_cents: number;
  collecte_vide: boolean;
}

/** Les quatre etapes, dans l'ordre du tunnel. Le libelle est celui du produit,
 * pas le nom technique de l'evenement. */
const ETAPES: { cle: string; libelle: string }[] = [
  { cle: 'scan_gratuit', libelle: 'Scan gratuit lancé' },
  { cle: 'email_debloque', libelle: 'E-mail débloqué' },
  { cle: 'inscription', libelle: 'Inscription' },
  { cle: 'abonnement', libelle: 'Abonnement actif' },
];

@Component({
  standalone: true,
  selector: 'app-admin-acquisition',
  imports: [MatIconModule],
  template: `
    <div class="p-6 space-y-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 class="text-white font-semibold text-lg">Acquisition</h1>
          <p class="text-gray-500 text-xs mt-0.5">
            D'où viennent les conversions, et lesquelles produisent du revenu.
          </p>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <span
            class="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-900"
          >
            <mat-icon class="text-[0.8rem] !h-3 !w-3">lock</mat-icon>
            Sans cookie · sans identifiant
          </span>
          <div class="flex rounded-lg border border-gray-700 overflow-hidden">
            @for (f of fenetres; track f.cle) {
              <button
                type="button"
                (click)="changerFenetre(f.cle)"
                class="text-xs px-3 py-1.5 border-r border-gray-700 last:border-r-0 transition-colors"
                [class]="
                  fenetre() === f.cle
                    ? 'bg-cyan-900/30 text-cyan-400'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                "
              >
                {{ f.libelle }}
              </button>
            }
          </div>
        </div>
      </div>

      @if (erreur()) {
        <div class="bg-red-950/40 border border-red-900 rounded-xl p-4 text-sm text-red-300">
          {{ erreur() }}
        </div>
      } @else if (chargement()) {
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          @for (i of [1, 2, 3, 4]; track i) {
            <div class="skeleton-shimmer rounded-xl h-20"></div>
          }
        </div>
        <div class="skeleton-shimmer rounded-xl h-64"></div>
      } @else if (donnees(); as d) {
        <!-- Indicateurs -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            <p class="text-gray-500 text-xs">Scans gratuits</p>
            <p class="text-white text-2xl font-semibold tabular-nums">
              {{ d.tunnel['scan_gratuit'] }}
            </p>
            <p class="text-gray-600 text-xs">
              dont {{ d.tunnel['email_debloque'] }} e-mails débloqués
            </p>
          </div>
          <div class="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            <p class="text-gray-500 text-xs">Inscriptions</p>
            <p class="text-white text-2xl font-semibold tabular-nums">
              {{ d.tunnel['inscription'] }}
            </p>
            <p class="text-gray-600 text-xs">{{ tauxInscription() }} des scans</p>
          </div>
          <div class="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            <p class="text-gray-500 text-xs">Abonnements</p>
            <p class="text-white text-2xl font-semibold tabular-nums">
              {{ d.tunnel['abonnement'] }}
            </p>
            <p class="text-gray-600 text-xs">signés sur la période</p>
          </div>
          <div class="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            <p class="text-gray-500 text-xs">MRR encore actif</p>
            <p class="text-emerald-400 text-2xl font-semibold tabular-nums">
              {{ euros(d.mrr_actif_cents) }}
            </p>
            <p class="text-gray-600 text-xs">
              {{ euros(d.mrr_signe_cents) }} signés, résiliations déduites
            </p>
          </div>
        </div>

        @if (d.collecte_vide) {
          <div
            class="border border-dashed border-gray-700 rounded-xl bg-gray-800/25 px-6 py-12 text-center"
          >
            <mat-icon class="text-cyan-500 !h-8 !w-8 text-3xl">trending_up</mat-icon>
            <h2 class="text-white text-sm font-semibold mt-3">
              La collecte tourne, personne n'a encore converti
            </h2>
            <p class="text-gray-500 text-xs mt-1.5 max-w-md mx-auto leading-relaxed">
              Les sources apparaîtront dès le premier scan gratuit. Pour attribuer une campagne,
              ajoutez un paramètre <code class="text-cyan-400">utm_source</code> à vos liens
              sortants.
            </p>
            <p
              class="inline-block mt-4 text-[11px] font-mono text-cyan-400 bg-cyan-500/10 border border-cyan-800 rounded-md px-3 py-1.5 break-all"
            >
              {{ exempleLien }}
            </p>
          </div>
        } @else {
          <div class="grid lg:grid-cols-3 gap-3 items-start">
            <!-- Sources -->
            <div class="lg:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-5">
              <h2 class="text-white font-semibold text-sm">Sources → revenu</h2>
              <p class="text-gray-600 text-xs mt-0.5 mb-4">
                Trié par revenu, pas par trafic. Une source sans abonné reste affichée : un zéro est
                une information.
              </p>
              <div class="overflow-x-auto">
                <table class="w-full tabular-nums">
                  <thead>
                    <tr class="text-gray-600 text-[10px] uppercase tracking-wider">
                      <th class="text-left font-medium pb-2 border-b border-gray-700">Source</th>
                      <th class="text-right font-medium pb-2 border-b border-gray-700">Scans</th>
                      <th class="text-right font-medium pb-2 border-b border-gray-700">Inscrits</th>
                      <th class="text-right font-medium pb-2 border-b border-gray-700">Abonnés</th>
                      <th class="text-right font-medium pb-2 border-b border-gray-700">Conv.</th>
                      <th class="text-right font-medium pb-2 border-b border-gray-700">MRR</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (s of d.sources; track s.source) {
                      <tr class="border-b border-gray-700/40 last:border-b-0">
                        <td class="text-white text-xs py-2.5">{{ s.source }}</td>
                        <td class="text-gray-400 text-xs text-right">{{ s.scans }}</td>
                        <td class="text-gray-400 text-xs text-right">{{ s.inscriptions }}</td>
                        <td class="text-gray-400 text-xs text-right">{{ s.abonnements }}</td>
                        <td
                          class="text-xs text-right"
                          [class]="s.abonnements ? 'text-gray-400' : 'text-gray-600'"
                        >
                          {{ s.taux_conversion }} %
                        </td>
                        <td class="text-right py-2.5">
                          <span
                            class="text-xs font-semibold"
                            [class]="s.mrr_cents ? 'text-emerald-400' : 'text-gray-600'"
                          >
                            {{ s.mrr_cents ? euros(s.mrr_cents) : '—' }}
                          </span>
                          <span class="block h-1 rounded-sm bg-gray-600/40 mt-1">
                            <span
                              class="block h-full rounded-sm bg-emerald-500"
                              [style.width.%]="part(s.mrr_cents)"
                            ></span>
                          </span>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Tunnel -->
            <div class="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
              <h2 class="text-white font-semibold text-sm">Tunnel de conversion</h2>
              <p class="text-gray-600 text-xs mt-0.5 mb-4">Toutes sources confondues</p>
              @for (e of etapes(); track e.cle) {
                <div class="mb-3 last:mb-0">
                  <div class="flex justify-between items-baseline text-xs text-gray-400">
                    <span>{{ e.libelle }}</span>
                    <b class="text-white font-semibold tabular-nums">{{ e.valeur }}</b>
                  </div>
                  <div class="h-5 rounded bg-gray-600/30 overflow-hidden mt-1">
                    <div
                      class="h-full"
                      [class]="e.dernier ? 'bg-emerald-500' : 'bg-cyan-600'"
                      [style.width.%]="e.largeur"
                    ></div>
                  </div>
                  @if (e.passage !== null) {
                    <p class="text-[11px] text-gray-600 mt-1 flex justify-between">
                      <span>↓ étape suivante</span>
                      <span class="text-amber-500 tabular-nums">{{ e.passage }} %</span>
                    </p>
                  }
                </div>
              }
            </div>
          </div>

          <!-- Pages -->
          @if (d.pages.length) {
            <div class="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
              <h2 class="text-white font-semibold text-sm">Pages d'atterrissage</h2>
              <p class="text-gray-600 text-xs mt-0.5 mb-4">
                Première page vue par ceux qui ont converti — le trafic brut n'est pas mesuré.
              </p>
              <div class="overflow-x-auto">
                <table class="w-full tabular-nums">
                  <thead>
                    <tr class="text-gray-600 text-[10px] uppercase tracking-wider">
                      <th class="text-left font-medium pb-2 border-b border-gray-700">Page</th>
                      <th class="text-right font-medium pb-2 border-b border-gray-700">Scans</th>
                      <th class="text-right font-medium pb-2 border-b border-gray-700">Inscrits</th>
                      <th class="text-right font-medium pb-2 border-b border-gray-700">Abonnés</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (p of d.pages; track p.page) {
                      <tr class="border-b border-gray-700/40 last:border-b-0">
                        <td class="text-white text-xs py-2.5 break-all">{{ p.page }}</td>
                        <td class="text-gray-400 text-xs text-right">{{ p.scans }}</td>
                        <td class="text-gray-400 text-xs text-right">{{ p.inscriptions }}</td>
                        <td class="text-gray-400 text-xs text-right">{{ p.abonnements }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          }

          <p class="text-gray-600 text-[11px] leading-relaxed max-w-3xl">
            Ce tableau ne montre pas où décrochent ceux qui ne convertissent jamais : sans
            identifiant de visiteur, il n'y a rien à relier. C'est le prix assumé de l'absence de
            bandeau de consentement.
          </p>
        }
      }
    </div>
  `,
})
export class AdminAcquisitionComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AdminAuthService);

  fenetres = [
    { cle: '30j', libelle: '30 j' },
    { cle: '90j', libelle: '90 j' },
    { cle: '12m', libelle: '12 mois' },
  ];

  fenetre = signal('90j');
  donnees = signal<VueAcquisition | null>(null);
  chargement = signal(true);
  erreur = signal('');

  exempleLien = 'https://rochercybersecurite.com/scan-gratuit?utm_source=linkedin';

  /** Étapes prêtes à afficher : largeur relative au premier palier, et taux de
   * passage vers l'étape suivante — c'est entre les étapes que la décision se
   * prend, pas au total. */
  etapes = computed(() => {
    const d = this.donnees();
    if (!d) return [];
    const base = d.tunnel[ETAPES[0].cle] || 0;
    return ETAPES.map((e, i) => {
      const valeur = d.tunnel[e.cle] || 0;
      const suivante = i < ETAPES.length - 1 ? d.tunnel[ETAPES[i + 1].cle] || 0 : null;
      return {
        cle: e.cle,
        libelle: e.libelle,
        valeur,
        largeur: base ? Math.max((valeur / base) * 100, valeur ? 1.5 : 0) : 0,
        passage: suivante === null || !valeur ? null : Math.round((suivante / valeur) * 1000) / 10,
        dernier: i === ETAPES.length - 1,
      };
    });
  });

  tauxInscription = computed(() => {
    const d = this.donnees();
    const scans = d?.tunnel['scan_gratuit'] || 0;
    if (!scans) return '—';
    return `${Math.round(((d?.tunnel['inscription'] || 0) / scans) * 1000) / 10} %`;
  });

  ngOnInit(): void {
    this.charger();
  }

  changerFenetre(cle: string): void {
    if (this.fenetre() === cle) return;
    this.fenetre.set(cle);
    this.charger();
  }

  private charger(): void {
    this.chargement.set(true);
    this.erreur.set('');
    this.http
      .get<VueAcquisition>(`/api/v1/admin/acquisition?fenetre=${this.fenetre()}`, {})
      .subscribe({
        next: d => {
          this.donnees.set(d);
          this.chargement.set(false);
        },
        error: () => {
          // Message explicite : cet onglet n'accepte QUE les comptes
          // administrateurs, jamais la clé partagée. Un « erreur 403 » brut
          // laisserait chercher longtemps.
          this.erreur.set(
            "Ces données ne sont accessibles qu'avec un compte administrateur. " +
              'La clé de secours ne les ouvre pas.'
          );
          this.chargement.set(false);
        },
      });
  }

  euros(cents: number): string {
    return `${(cents / 100).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} €`;
  }

  part(cents: number): number {
    const max = Math.max(...(this.donnees()?.sources.map(s => s.mrr_cents) || [0]), 1);
    return (cents / max) * 100;
  }
}
