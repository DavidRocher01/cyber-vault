import { Injectable, inject } from '@angular/core';
import { Title, Meta } from '@angular/platform-browser';
import { ActivatedRouteSnapshot, RouterStateSnapshot, TitleStrategy } from '@angular/router';

/**
 * Pose le titre ET la meta description a partir de la ROUTE.
 *
 * POURQUOI CE FICHIER EXISTE. Les titres vivaient deja sur les routes
 * (`title:`), mais les descriptions etaient posees a la main dans les
 * composants, un `meta.updateTag` a la fois. Resultat mesure le 2026-08-09 :
 * NEUF des 23 pages annoncees au sitemap n'avaient AUCUNE description, dont
 * `/nis2` — la page que le lot 1 venait tout juste d'ouvrir a l'indexation.
 *
 * Sans description, Google fabrique lui-meme l'extrait affiche sous le lien,
 * en piochant dans la page. On laisse donc un moteur rediger l'argumentaire
 * commercial a notre place.
 *
 * DECLARER LA DESCRIPTION A COTE DU TITRE met les deux au meme endroit : une
 * page nouvelle les gagne d'un seul geste, et l'oubli se voit a la lecture de
 * la route plutot qu'en inspectant un composant.
 *
 * CETTE STRATEGIE N'ECRASE JAMAIS UNE DESCRIPTION QU'ELLE N'A PAS DECLAREE.
 * Quinze composants posent encore la leur dans `ngOnInit`, qui s'execute AVANT
 * cette strategie : ecrire inconditionnellement les effacerait toutes. On
 * n'agit donc que si la route declare quelque chose — la migration de ces
 * quinze pages peut se faire plus tard, page par page, sans rien casser.
 */
@Injectable({ providedIn: 'root' })
export class SeoStrategy extends TitleStrategy {
  private readonly titre = inject(Title);
  private readonly meta = inject(Meta);

  override updateTitle(etat: RouterStateSnapshot): void {
    const titre = this.buildTitle(etat);
    if (titre !== undefined) this.titre.setTitle(titre);

    const description = this.descriptionDe(etat.root);
    if (description) this.meta.updateTag({ name: 'description', content: description });
  }

  /** La description declaree la PLUS PROFONDE l'emporte : une route enfant
   *  decrit sa page mieux que le parent qui la contient. */
  private descriptionDe(racine: ActivatedRouteSnapshot): string | null {
    let trouvee: string | null = null;
    for (let r: ActivatedRouteSnapshot | undefined = racine; r; r = r.firstChild ?? undefined) {
      const declaree = r.data?.['description'];
      if (typeof declaree === 'string' && declaree.trim()) trouvee = declaree;
    }
    return trouvee;
  }
}
