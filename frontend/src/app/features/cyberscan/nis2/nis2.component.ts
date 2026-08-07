import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ComplianceApiService } from '../services/compliance-api.service';
import { PieceJustificative } from '../services/cyberscan.service';
import { BillingService } from '../services/billing.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import {
  complianceStatusLabel,
  complianceStatusIcon,
  complianceStatusClass,
  complianceStatusColor,
  complianceScoreColor,
  complianceScoreLabel,
} from '../shared/compliance-status.util';
import { formatFrDate } from '../../../shared/date-utils';

export type Nis2Status = 'compliant' | 'partial' | 'non_compliant' | 'na';

/** Produit interne qui comble l'écart pointé par un item du référentiel.
 *
 * Renseigné côté backend (NIS2_CATEGORIES) uniquement pour les items où un
 * produit répond réellement au manque — pas d'approximation commerciale.
 */
export interface Nis2Remediation {
  produit: string;
  route: string;
}

/** Mesure objective detenue par la plateforme pour un item du referentiel.
 *
 * Elle NE remplit PAS le questionnaire : l'utilisateur declare, la plateforme
 * mesure. Une auto-evaluation pre-remplie n'est plus une declaration et perd sa
 * valeur devant un auditeur.
 */
export interface Nis2Preuve {
  organisations: number;
  apprenants: number;
  termines: number;
  pct: number;
}

export interface Nis2Item {
  id: string;
  label: string;
  desc: string;
  /** Article de la directive (UE) 2022/2555 auquel l'item se rattache.
   *  Rattachement indicatif, pas une analyse juridique. */
  article?: string;
  remediation?: Nis2Remediation;
}

export interface Nis2Category {
  id: string;
  label: string;
  icon: string;
  items: Nis2Item[];
}

@Component({
  standalone: true,
  selector: 'app-nis2',
  imports: [
    RouterLink,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    NavButtonsComponent,
  ],
  templateUrl: './nis2.component.html',
  styleUrl: './nis2.component.css',
})
export class Nis2Component implements OnInit {
  private complianceApi = inject(ComplianceApiService);
  private billing = inject(BillingService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private snack = inject(MatSnackBar);

  loading = signal(true);
  saving = signal(false);
  exporting = signal(false);
  exportingAuditor = signal(false);

  // Export PDF réservé aux plans payants (allow_conformity_export). Le score reste
  // visible au Gratuit (accroche de conversion) ; seul l'export est verrouillé.
  private subLoaded = signal(false);
  canExport = signal(false);
  // Vrai uniquement une fois l'abonnement chargé et l'export non autorisé : évite
  // d'afficher le CTA d'upgrade à un payant pendant le chargement.
  readonly showUpgrade = computed(() => this.subLoaded() && !this.canExport());

  // LE SUJET DE L'EVALUATION, lu dans l'URL.
  //
  // `null` → la mienne (`/nis2`). Un identifiant → le dossier que le consultant
  // monte pour ce client (`/clients/:clientId/nis2`). Le même écran sert les
  // deux : seul le préfixe des routes API change, côté service.
  clientId = signal<number | null>(null);
  readonly modeClient = computed(() => this.clientId() !== null);

  categories = signal<Nis2Category[]>([]);
  preuves = signal<Record<string, Nis2Preuve>>({});
  // Documents déposés par l'utilisateur, par critère. À ne pas confondre avec
  // `preuves` juste au-dessus, qui sont les mesures de la plateforme.
  pieces = signal<Record<string, PieceJustificative[]>>({});
  // Critère dont le dépôt est en cours — pour n'afficher le spinner que sur la
  // ligne concernée, et non sur les 34.
  depotEnCours = signal<string | null>(null);
  items = signal<Record<string, Nis2Status>>({});
  score = signal(0);
  updatedAt = signal<string | null>(null);

  // Status cycle: non_compliant → partial → compliant → na → non_compliant
  private readonly CYCLE: Nis2Status[] = ['non_compliant', 'partial', 'compliant', 'na'];
  readonly STATUS_LIST: Nis2Status[] = ['compliant', 'partial', 'non_compliant', 'na'];

  ngOnInit() {
    // Lu de façon synchrone : le paramètre doit être posé avant le premier
    // appel, sinon le dossier d'un client serait demandé sur la route « moi ».
    const brut = this.route.snapshot.paramMap.get('clientId');
    this.clientId.set(brut ? Number(brut) : null);

    this.billing.getMySubscription().subscribe({
      next: sub => {
        this.canExport.set(!!sub?.plan?.allow_conformity_export);
        this.subLoaded.set(true);
      },
      error: () => this.subLoaded.set(true),
    });

    this.complianceApi.getNis2Assessment(this.clientId()).subscribe({
      next: data => {
        // Narrowing au bord de l'API : le backend renvoie des chaînes/objets
        // generiques dont les valeurs sont garanties valides pour ces types.
        this.categories.set((data.categories ?? []) as Nis2Category[]);
        this.items.set((data.items ?? {}) as Record<string, Nis2Status>);
        this.preuves.set((data.preuves ?? {}) as Record<string, Nis2Preuve>);
        this.pieces.set(data.pieces ?? {});
        this.score.set(data.score ?? 0);
        this.updatedAt.set(data.updated_at ?? null);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snack.open('Erreur lors du chargement', 'Fermer', { duration: 4000 });
      },
    });
  }

  getStatus(itemId: string): Nis2Status {
    return this.items()[itemId] ?? 'non_compliant';
  }

  /** Mesure détenue par la plateforme pour cet item, s'il y en a une. */
  preuve(itemId: string): Nis2Preuve | null {
    return this.preuves()[itemId] ?? null;
  }

  // ── Pièces justificatives ──────────────────────────────────────────────────

  /** Documents que l'utilisateur a déposés pour ce critère. */
  piecesDe(itemId: string): PieceJustificative[] {
    return this.pieces()[itemId] ?? [];
  }

  /** Vrai seulement si l'analyse antivirus a conclu que le fichier est sain.
   *
   * Toute autre valeur — en analyse, rejeté, indéterminé — n'ouvre pas le
   * document. Une valeur inconnue ne vaut jamais « sain » : c'est la même règle
   * que côté serveur, et l'écran ne doit pas proposer un lien qui répondra 409.
   */
  pieceOuvrable(piece: PieceJustificative): boolean {
    return piece.statut_analyse === 'sain';
  }

  etatPiece(piece: PieceJustificative): string {
    switch (piece.statut_analyse) {
      case 'sain':
        return 'Vérifié';
      case 'en_analyse':
        return 'Analyse antivirus en cours';
      case 'rejete':
        return 'Rejeté par l’antivirus';
      default:
        return 'Vérification non concluante';
    }
  }

  tailleLisible(octets: number): string {
    if (octets < 1024) return `${octets} o`;
    if (octets < 1024 * 1024) return `${Math.round(octets / 1024)} Ko`;
    return `${(octets / (1024 * 1024)).toFixed(1)} Mo`;
  }

  deposerPiece(itemId: string, evt: Event) {
    const input = evt.target as HTMLInputElement;
    const fichier = input.files?.[0];
    if (!fichier) return;
    // Le champ est vidé tout de suite : sans cela, redéposer le même fichier
    // après une erreur ne déclencherait aucun évènement `change`.
    input.value = '';

    this.depotEnCours.set(itemId);
    this.complianceApi.deposerPiece(itemId, fichier, this.clientId()).subscribe({
      next: piece => {
        this.pieces.update(m => ({ ...m, [itemId]: [...(m[itemId] ?? []), piece] }));
        this.depotEnCours.set(null);
        this.snack.open('Pièce ajoutée', 'Fermer', { duration: 3000 });
      },
      error: err => {
        this.depotEnCours.set(null);
        // Le message du serveur est celui qui informe : quota atteint, contenu
        // qui ne correspond pas à l'extension, abonnement requis. Le remplacer
        // par un texte générique priverait l'utilisateur du seul indice utile.
        this.snack.open(err?.error?.detail ?? 'Le dépôt a échoué. Réessayez.', 'Fermer', {
          duration: 6000,
        });
      },
    });
  }

  retirerPiece(itemId: string, piece: PieceJustificative) {
    this.complianceApi.retirerPiece(piece.id, this.clientId()).subscribe({
      next: () => {
        this.pieces.update(m => ({
          ...m,
          [itemId]: (m[itemId] ?? []).filter(p => p.id !== piece.id),
        }));
        this.snack.open('Pièce retirée', 'Fermer', { duration: 3000 });
      },
      error: err =>
        this.snack.open(err?.error?.detail ?? 'Le retrait a échoué.', 'Fermer', {
          duration: 5000,
        }),
    });
  }

  ouvrirPiece(piece: PieceJustificative) {
    this.complianceApi.lienPiece(piece.id, this.clientId()).subscribe({
      next: r => window.open(r.url, '_blank'),
      error: err =>
        this.snack.open(err?.error?.detail ?? 'Ouverture impossible.', 'Fermer', {
          duration: 5000,
        }),
    });
  }

  /** Vrai si l'item a été EXPLICITEMENT renseigné comme un écart.
   *
   * getStatus() retourne 'non_compliant' par défaut pour les items non
   * renseignés : s'en servir afficherait la remédiation sur une évaluation
   * vierge, avant que l'utilisateur ait rien déclaré. On exige donc une réponse
   * explicite.
   */
  aUnEcartDeclare(itemId: string): boolean {
    const statut = this.items()[itemId];
    return statut === 'non_compliant' || statut === 'partial';
  }

  toggle(itemId: string) {
    const current = this.getStatus(itemId);
    const idx = this.CYCLE.indexOf(current);
    const next = this.CYCLE[(idx + 1) % this.CYCLE.length];
    this.items.update(m => ({ ...m, [itemId]: next }));
    this.recalcScore();
  }

  setStatus(itemId: string, status: Nis2Status) {
    this.items.update(m => ({ ...m, [itemId]: status }));
    this.recalcScore();
  }

  recalcScore() {
    // Utiliser TOUS les items des catégories comme dénominateur,
    // pas seulement ceux explicitement renseignés dans le map.
    // Les items non renseignés ont getStatus() = 'non_compliant' = 0 pts.
    const allIds = this.categories().flatMap(cat => cat.items.map(i => i.id));
    const vals = allIds.map(id => this.getStatus(id)).filter(v => v !== 'na');
    if (!vals.length) {
      this.score.set(0);
      return;
    }
    const pts = vals.reduce((s, v) => s + (v === 'compliant' ? 2 : v === 'partial' ? 1 : 0), 0);
    this.score.set(Math.round((pts / (vals.length * 2)) * 100));
  }

  resetAll() {
    this.items.set({});
    this.recalcScore();
  }

  private get _fullItems(): Record<string, string> {
    const allIds = this.categories().flatMap(cat => cat.items.map(i => i.id));
    const full: Record<string, string> = {};
    for (const id of allIds) full[id] = this.getStatus(id);
    return full;
  }

  save() {
    this.saving.set(true);
    this.complianceApi.saveNis2Assessment(this._fullItems, this.clientId()).subscribe({
      next: data => {
        this.score.set(data.score);
        this.updatedAt.set(data.updated_at);
        this.saving.set(false);
        this.snack.open('Évaluation sauvegardée', 'OK', { duration: 3000 });
      },
      error: () => {
        this.saving.set(false);
        this.snack.open('Erreur lors de la sauvegarde', 'Fermer', { duration: 4000 });
      },
    });
  }

  /**
   * Verrou d'export payant : message explicite (pas une « erreur du site ») +
   * action directe vers la grille tarifaire. Bascule aussi l'UI en mode Gratuit.
   */
  private notifyExportLocked(): void {
    this.canExport.set(false);
    this.subLoaded.set(true);
    const ref = this.snack.open(
      "L'export PDF est réservé aux plans payants (dès Starter).",
      'Voir les offres',
      { duration: 7000 }
    );
    ref.onAction().subscribe(() => {
      this.router.navigate(['/dashboard'], { queryParams: { upgrade: 'true' } });
    });
  }

  exportPdf() {
    this.exporting.set(true);
    // Sauvegarde automatique avant export pour garantir la cohérence PDF/app
    this.complianceApi.saveNis2Assessment(this._fullItems, this.clientId()).subscribe({
      next: data => {
        this.score.set(data.score);
        this.updatedAt.set(data.updated_at);
        this._downloadPdf();
      },
      error: () => {
        this.exporting.set(false);
        this.snack.open('Erreur lors de la sauvegarde avant export', 'Fermer', { duration: 4000 });
      },
    });
  }

  private _downloadPdf() {
    this.complianceApi.downloadNis2PdfBlob().subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'cyberscan_nis2_conformite.pdf';
        a.click();
        URL.revokeObjectURL(url);
        this.exporting.set(false);
      },
      error: err => {
        this.exporting.set(false);
        if (err?.status === 403) {
          this.notifyExportLocked();
          return;
        }
        this.snack.open("Erreur lors de l'export PDF", 'Fermer', { duration: 4000 });
      },
    });
  }

  exportAuditorPdf() {
    this.exportingAuditor.set(true);
    this.complianceApi.saveNis2Assessment(this._fullItems, this.clientId()).subscribe({
      next: data => {
        this.score.set(data.score);
        this.updatedAt.set(data.updated_at);
        this.complianceApi.downloadNis2AuditorPdfBlob(this.clientId()).subscribe({
          next: blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'cyberscan_nis2_pret_a_deposer.pdf';
            a.click();
            URL.revokeObjectURL(url);
            this.exportingAuditor.set(false);
          },
          error: err => {
            this.exportingAuditor.set(false);
            if (err?.status === 403) {
              this.notifyExportLocked();
              return;
            }
            this.snack.open("Erreur lors de l'export du document officiel", 'Fermer', {
              duration: 4000,
            });
          },
        });
      },
      error: () => {
        this.exportingAuditor.set(false);
        this.snack.open('Erreur lors de la sauvegarde avant export', 'Fermer', { duration: 4000 });
      },
    });
  }

  // ── Helpers ────────────────────────────────────────────────────────────

  statusLabel(s: string): string {
    return complianceStatusLabel(s);
  }

  statusIcon(s: string): string {
    return complianceStatusIcon(s);
  }

  statusClass(s: string): string {
    return complianceStatusClass(s);
  }

  statusColor(s: string): string {
    return complianceStatusColor(s);
  }

  scoreColor(n: number): string {
    return complianceScoreColor(n);
  }

  scoreLabel(n: number): string {
    return complianceScoreLabel(n);
  }

  catCompliance(cat: Nis2Category): {
    compliant: number;
    partial: number;
    nc: number;
    total: number;
  } {
    const its = cat.items;
    return {
      compliant: its.filter(i => this.getStatus(i.id) === 'compliant').length,
      partial: its.filter(i => this.getStatus(i.id) === 'partial').length,
      nc: its.filter(i => this.getStatus(i.id) === 'non_compliant').length,
      total: its.length,
    };
  }

  catScore(cat: Nis2Category): number {
    const scorable = cat.items.filter(i => this.getStatus(i.id) !== 'na');
    if (!scorable.length) return 0;
    const pts = scorable.reduce((s, i) => {
      const v = this.getStatus(i.id);
      return s + (v === 'compliant' ? 2 : v === 'partial' ? 1 : 0);
    }, 0);
    return Math.round((pts / (scorable.length * 2)) * 100);
  }

  formatDate(d: string | null): string {
    return formatFrDate(d, 'datetime');
  }

  readonly totalItems = computed(() => this.categories().reduce((s, c) => s + c.items.length, 0));

  private readonly allItemIds = computed(() =>
    this.categories().flatMap(cat => cat.items.map(i => i.id))
  );

  readonly compliantCount = computed(
    () => this.allItemIds().filter(id => this.getStatus(id) === 'compliant').length
  );
  readonly partialCount = computed(
    () => this.allItemIds().filter(id => this.getStatus(id) === 'partial').length
  );
  readonly ncCount = computed(
    () => this.allItemIds().filter(id => this.getStatus(id) === 'non_compliant').length
  );
  readonly naCount = computed(
    () => this.allItemIds().filter(id => this.getStatus(id) === 'na').length
  );
}
