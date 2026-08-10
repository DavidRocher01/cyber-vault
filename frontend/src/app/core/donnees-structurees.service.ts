import { DOCUMENT, Injectable, inject } from '@angular/core';
import { NavigationStart, Router } from '@angular/router';

/** Une question et sa reponse, telles que les pages les declarent deja. */
export interface QuestionReponse {
  question: string;
  answer: string;
}

/**
 * Pose les donnees structurees (JSON-LD) de la page courante.
 *
 * POURQUOI. `index.html` porte un bloc `SoftwareApplication` global, servi
 * identique sur les 43 pages. Rien ne decrit ce que chaque page contient
 * REELLEMENT — alors que trois d'entre elles portent une FAQ, le format que
 * Google sait le mieux mettre en avant dans ses resultats.
 *
 * LA SOURCE RESTE LE TABLEAU DU COMPOSANT. Les questions vivent deja dans le
 * code des pages : les recopier dans un bloc JSON-LD creerait deux verites qui
 * divergeraient a la premiere correction. On derive, on ne duplique pas.
 *
 * LE BLOC EST RETIRE A CHAQUE DEBUT DE NAVIGATION. Dans une application d'une
 * seule page, un bloc pose puis oublie SUIT le visiteur : la FAQ du RSSI
 * externalise se retrouverait declaree sur la page de tarifs. On efface donc
 * sur `NavigationStart`, et chaque page repose le sien pendant son activation.
 */
@Injectable({ providedIn: 'root' })
export class DonneesStructureesService {
  private readonly doc = inject(DOCUMENT);
  private readonly router = inject(Router);

  /** Marqueur : distingue NOTRE bloc de celui, statique, d'`index.html`. */
  private static readonly MARQUEUR = 'data-jsonld-page';

  constructor() {
    this.router.events.subscribe(e => {
      if (e instanceof NavigationStart) this.retirer();
    });
  }

  /** Declare une FAQ pour la page courante. Sans question, on ne pose rien :
   *  un `FAQPage` vide est un signal trompeur, pas une absence. */
  poserFaq(questions: readonly QuestionReponse[]): void {
    if (!questions.length) return;

    this.poser({
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: questions.map(q => ({
        '@type': 'Question',
        name: q.question,
        acceptedAnswer: { '@type': 'Answer', text: q.answer },
      })),
    });
  }

  poser(donnees: object): void {
    this.retirer();
    const script = this.doc.createElement('script');
    script.setAttribute('type', 'application/ld+json');
    script.setAttribute(DonneesStructureesService.MARQUEUR, '');
    script.textContent = JSON.stringify(donnees);
    this.doc.head.appendChild(script);
  }

  private retirer(): void {
    this.doc
      .querySelectorAll(`script[${DonneesStructureesService.MARQUEUR}]`)
      .forEach(n => n.remove());
  }
}
