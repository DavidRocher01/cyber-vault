import { ErrorHandler, Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

/**
 * Recharge la page quand un module de route ne peut plus être téléchargé.
 *
 * LE PROBLÈME, OBSERVÉ EN PRODUCTION LE 2026-08-07. Le déploiement synchronise
 * le bundle avec `aws s3 sync --delete` : les fichiers dont l'empreinte a changé
 * sont **supprimés**. Un onglet resté ouvert pendant une bascule continue de
 * tourner sur l'ancienne application et demande des morceaux qui n'existent
 * plus. Comme les pages sont chargées à la demande (`loadComponent`), la
 * navigation échoue — et Angular ne dit rien : le clic paraît simplement mort.
 *
 * Vérifié : un chunk du déploiement précédent répondait 403 après la bascule,
 * tandis qu'un chunk au contenu inchangé — donc à la même empreinte — répondait
 * toujours 200.
 *
 * CE QUE FAIT CE GESTIONNAIRE. Il recharge la page une fois : le navigateur
 * récupère l'`index.html` à jour, donc les bonnes empreintes, et l'utilisateur
 * atterrit là où il voulait aller. Un bref rechargement vaut mieux qu'un bouton
 * qui ne répond pas.
 *
 * IL NE RECHARGE QU'UNE FOIS, ET C'EST ESSENTIEL. Si le morceau manque pour une
 * autre raison — déploiement à moitié synchronisé, cache intermédiaire — un
 * rechargement systématique enfermerait l'utilisateur dans une boucle. Le
 * garde-fou est posé en `sessionStorage` : il vit le temps de l'onglet, et une
 * nouvelle visite repart proprement.
 *
 * TOUTE AUTRE ERREUR EST TRANSMISE au gestionnaire par défaut. Ce n'est pas un
 * attrape-tout : l'avaler priverait la console des erreurs réelles.
 */

/** Motifs d'échec de `import()` dynamique, un par moteur de rendu. */
const MOTIFS = [
  'ChunkLoadError', // webpack
  'Loading chunk', // webpack
  'Failed to fetch dynamically imported module', // Chromium
  'error loading dynamically imported module', // Firefox
  'Importing a module script failed', // Safari
  'Loading CSS chunk', // styles d'une route
];

const CLE_GARDE = 'rechargement-module-manquant';

export function estEchecDeChargement(erreur: unknown): boolean {
  const texte = `${(erreur as { message?: string })?.message ?? ''} ${String(erreur ?? '')}`;
  return MOTIFS.some(m => texte.includes(m));
}

@Injectable()
export class ChunkReloadHandler implements ErrorHandler {
  private plateforme = inject(PLATFORM_ID);
  private defaut = new ErrorHandler();

  handleError(erreur: unknown): void {
    if (!estEchecDeChargement(erreur) || !isPlatformBrowser(this.plateforme)) {
      this.defaut.handleError(erreur);
      return;
    }

    if (this.dejaRecharge()) {
      // Le rechargement n'a pas suffi : ce n'est pas un simple bundle périmé.
      // On laisse l'erreur remonter plutôt que de boucler en silence.
      this.defaut.handleError(erreur);
      return;
    }

    // ON NE RECHARGE QUE SI LE GARDE-FOU A PU ÊTRE POSÉ. Si l'écriture échoue,
    // le prochain chargement relirait « jamais rechargé » et repartirait : une
    // boucle infinie, pire que le bouton mort qu'on répare.
    if (!this.marquerRechargement()) {
      this.defaut.handleError(erreur);
      return;
    }
    window.location.reload();
  }

  /** `sessionStorage` peut lever (mode privé strict, stockage désactivé).
   *  En cas de doute on considère qu'on a déjà rechargé : ne rien faire est
   *  préférable à une boucle de rechargements. */
  private dejaRecharge(): boolean {
    try {
      return sessionStorage.getItem(CLE_GARDE) !== null;
    } catch {
      return true;
    }
  }

  /** Renvoie `false` si le garde-fou n'a pas pu être écrit. */
  private marquerRechargement(): boolean {
    try {
      sessionStorage.setItem(CLE_GARDE, '1');
      return true;
    } catch {
      return false;
    }
  }
}
