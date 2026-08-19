import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

/**
 * Session de l'apprenant du portail de sensibilisation — état seul, pas de HTTP.
 *
 * POURQUOI CE SERVICE EXISTE, ET POURQUOI DANS `core/`.
 *
 * `awarenessLearnerGuard` vit dans `core/guards/`, comme tous les gardes du
 * projet, et il avait besoin de savoir si une session existe. Il allait donc la
 * chercher dans `features/cyberscan/services/awareness.service.ts` — un import
 * de `core/` vers `features/`, à rebours de la règle de couches : c'était le
 * SEUL de tout le dossier, les 49 autres fichiers allant dans le bon sens.
 *
 * Déplacer le garde dans la fonctionnalité aurait règlé le sens de la flèche en
 * contredisant `CLAUDE.md`, qui place les gardes ici. On a donc déplacé ce dont
 * le garde a besoin — l'état de session — plutôt que le garde lui-même. Le
 * service métier de sensibilisation, lui, reste dans sa fonctionnalité : il
 * porte 498 lignes d'appels HTTP qui n'ont rien à faire dans le noyau.
 *
 * `isPlatformBrowser` N'EST PAS DÉCORATIF ICI. La lecture se faisait dans un
 * initialiseur de champ d'un service `providedIn: 'root'` — donc à la
 * construction, prérendu compris, où `localStorage` n'existe pas. Elle ne
 * passait que grâce au `try/catch` qui l'entourait : protégée par accident,
 * et en violation de la règle SSR du projet. L'écriture et l'effacement, eux,
 * n'avaient aucune protection.
 */

const CLE_SESSION = 'awareness_learner_token';

export interface LearnerSession {
  learner_id: number;
  organization_id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  access_token: string;
}

@Injectable({ providedIn: 'root' })
export class AwarenessSessionService {
  // Déclaré AVANT `session` : les champs s'initialisent dans l'ordre d'écriture,
  // et `charger()` a besoin de savoir où il tourne.
  private readonly navigateur = isPlatformBrowser(inject(PLATFORM_ID));

  readonly session = signal<LearnerSession | null>(this.charger());

  enregistrer(session: LearnerSession): void {
    if (this.navigateur) {
      localStorage.setItem(CLE_SESSION, JSON.stringify(session));
    }
    this.session.set(session);
  }

  effacer(): void {
    if (this.navigateur) {
      localStorage.removeItem(CLE_SESSION);
    }
    this.session.set(null);
  }

  private charger(): LearnerSession | null {
    if (!this.navigateur) {
      return null;
    }
    try {
      const brut = localStorage.getItem(CLE_SESSION);
      return brut ? JSON.parse(brut) : null;
    } catch {
      // Contenu illisible : on repart sans session plutôt que de casser le
      // démarrage de l'application.
      return null;
    }
  }
}
