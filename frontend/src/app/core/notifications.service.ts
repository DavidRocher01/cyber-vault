import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

/**
 * Notifications ephemeres — remplace `@ngneat/hot-toast`.
 *
 * POURQUOI CE SERVICE EXISTE. `@ngneat/hot-toast` n'a plus ete publie depuis le
 * 6 aout 2024, et sa derniere version declare ne fonctionner qu'avec Angular 17.
 * Le depot l'installait quand meme, parce que `.npmrc` porte
 * `legacy-peer-deps=true` — npm ignore alors les conflits au lieu de les
 * signaler. La dependance ne bloquait donc rien visiblement, jusqu'a la montee
 * en Angular 22 ou elle est devenue le SEUL obstacle qu'aucune mise a jour
 * amont ne resoudra jamais.
 *
 * LES NOMS `success`/`error`/`warning` SONT CONSERVES A DESSEIN : la migration
 * se reduit alors a un changement d'import sur les huit appels existants, et les
 * simulacres des specs restent valides. Un renommage aurait multiplie les
 * occasions d'oublier un appel, pour un gain nul.
 */

export type TonNotification = 'succes' | 'erreur' | 'avertissement';

export interface NotificationAffichee {
  readonly id: number;
  readonly texte: string;
  readonly ton: TonNotification;
}

/** Duree d'affichage, reprise de la configuration `hot-toast` precedente. */
const DUREE_MS = 3000;

@Injectable({ providedIn: 'root' })
export class NotificationsService {
  private readonly navigateur = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly _actives = signal<readonly NotificationAffichee[]>([]);

  readonly actives = this._actives.asReadonly();

  private suivant = 0;
  private readonly minuteurs = new Map<number, ReturnType<typeof setTimeout>>();

  success(texte: string): void {
    this.afficher(texte, 'succes');
  }

  error(texte: string): void {
    this.afficher(texte, 'erreur');
  }

  warning(texte: string): void {
    this.afficher(texte, 'avertissement');
  }

  fermer(id: number): void {
    const minuteur = this.minuteurs.get(id);
    if (minuteur !== undefined) {
      clearTimeout(minuteur);
      this.minuteurs.delete(id);
    }
    this._actives.update(liste => liste.filter(n => n.id !== id));
  }

  private afficher(texte: string, ton: TonNotification): void {
    // RIEN NE S'AFFICHE COTE SERVEUR, et ce n'est pas qu'une precaution de
    // forme : l'intercepteur HTTP appelle `warning()` sur un 429, y compris
    // pendant le prerendu. Un `setTimeout` de trois secondes y retiendrait la
    // stabilite de l'application et retarderait d'autant la generation de la
    // page. Une notification est une affordance de navigateur ; sur le serveur,
    // elle n'a simplement pas de sens.
    if (!this.navigateur) {
      return;
    }

    // UN MEME MESSAGE NE S'EMPILE PAS. Le seul appelant automatique est
    // l'intercepteur sur un 429 : une page qui lance six requetes en parallele
    // les voit toutes refusees, et afficherait six fois la meme phrase. On
    // repousse plutot l'echeance de celle deja visible.
    const deja = this._actives().find(n => n.texte === texte && n.ton === ton);
    if (deja) {
      this.reporter(deja.id);
      return;
    }

    const id = ++this.suivant;
    this._actives.update(liste => [...liste, { id, texte, ton }]);
    this.reporter(id);
  }

  private reporter(id: number): void {
    const precedent = this.minuteurs.get(id);
    if (precedent !== undefined) {
      clearTimeout(precedent);
    }
    this.minuteurs.set(
      id,
      setTimeout(() => this.fermer(id), DUREE_MS)
    );
  }
}
