import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Injector, PLATFORM_ID, runInInjectionContext } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { of, throwError } from 'rxjs';

import { MaintenanceBannerComponent } from './maintenance-banner.component';

const CLE_MASQUAGE = 'cyberscan_maintenance_dismissed';

interface Config {
  active: boolean;
  level?: 'info' | 'warning' | 'critical';
  message?: string;
  until?: string | null;
}

/**
 * Le bandeau est pilote au RUNTIME par un fichier depose sur S3 : aucun test de
 * build ne peut le valider. Ce spec est donc le seul endroit ou l'on verifie
 * qu'un fichier mal forme n'affiche pas un bandeau vide en production.
 */
function creer(reponse: Config | null | 'erreur', plateforme: 'browser' | 'server' = 'browser') {
  const get = vi.fn(() =>
    reponse === 'erreur' ? throwError(() => new Error('reseau')) : of(reponse)
  );

  const injector = Injector.create({
    providers: [
      { provide: PLATFORM_ID, useValue: plateforme },
      { provide: HttpClient, useValue: { get } },
    ],
  });
  const composant = runInInjectionContext(injector, () => new MaintenanceBannerComponent());
  composant.ngOnInit();
  return { composant, get };
}

describe('MaintenanceBannerComponent', () => {
  beforeEach(() => localStorage.clear());

  describe('ce qui declenche l affichage', () => {
    it('affiche le message quand la configuration est active', () => {
      const { composant } = creer({ active: true, message: 'Migration de la base a 22h' });

      expect(composant.visible()).toBe(true);
      expect(composant.message()).toBe('Migration de la base a 22h');
    });

    it('reste masque quand la configuration est inactive', () => {
      const { composant } = creer({ active: true, message: 'x' });
      expect(composant.visible()).toBe(true);

      const { composant: eteint } = creer({ active: false, message: 'x' });
      expect(eteint.visible()).toBe(false);
    });

    it('reste masque si le message est absent, meme actif', () => {
      // Le cas d'une edition ratee du JSON : `active: true` sans texte
      // afficherait une barre vide en haut du site, sans rien dire.
      expect(creer({ active: true }).composant.visible()).toBe(false);
      expect(creer({ active: true, message: '' }).composant.visible()).toBe(false);
    });

    it('reste masque si le fichier est injoignable', () => {
      // `catchError` doit avaler la panne : un bandeau de maintenance ne doit
      // jamais empecher le site de s'afficher.
      const { composant } = creer('erreur');
      expect(composant.visible()).toBe(false);
    });

    it('reste masque si la reponse est vide', () => {
      expect(creer(null).composant.visible()).toBe(false);
    });
  });

  describe('masquage par l utilisateur', () => {
    it('dismiss() enregistre le message courant et referme', () => {
      const { composant } = creer({ active: true, message: 'Coupure prevue' });

      composant.dismiss();

      expect(composant.visible()).toBe(false);
      expect(localStorage.getItem(CLE_MASQUAGE)).toBe('Coupure prevue');
    });

    it('ne reaffiche pas un message deja masque', () => {
      localStorage.setItem(CLE_MASQUAGE, 'Coupure prevue');

      const { composant } = creer({ active: true, message: 'Coupure prevue' });

      expect(composant.visible()).toBe(false);
    });

    it('reaffiche des que le message CHANGE', () => {
      localStorage.setItem(CLE_MASQUAGE, 'Coupure prevue');

      const { composant } = creer({ active: true, message: 'Incident en cours' });

      // C'est l'interet d'indexer le masquage sur le texte plutot que sur un
      // booleen : une nouvelle annonce reprend la parole meme si la precedente
      // avait ete ecartee.
      expect(composant.visible()).toBe(true);
    });
  });

  describe('niveau de gravite', () => {
    it('retient le niveau annonce', () => {
      expect(creer({ active: true, message: 'm', level: 'critical' }).composant.level()).toBe(
        'critical'
      );
    });

    it('retombe sur "warning" quand le niveau est absent', () => {
      expect(creer({ active: true, message: 'm' }).composant.level()).toBe('warning');
    });

    it('donne une icone et une teinte distinctes a chaque niveau', () => {
      const niveaux = ['info', 'warning', 'critical'] as const;

      const icones = niveaux.map(n => creer({ active: true, message: 'm', level: n }).composant);
      const paires = icones.map(c => [c.icon(), c.barClasses()] as const);

      // Si deux niveaux rendaient la meme chose, un incident critique
      // ressemblerait a une simple information.
      expect(new Set(paires.map(p => p[0])).size).toBe(3);
      expect(new Set(paires.map(p => p[1])).size).toBe(3);
    });
  });

  describe('echeance affichee', () => {
    it('formate une date valide', () => {
      const { composant } = creer({
        active: true,
        message: 'm',
        until: '2026-09-01T22:00:00Z',
      });

      expect(composant.untilLabel()).toContain("jusqu'à");
    });

    it.each([[null], [undefined], ['pas une date']])(
      'n affiche rien pour une echeance inexploitable (%s)',
      valeur => {
        const { composant } = creer({
          active: true,
          message: 'm',
          until: valeur as string | null,
        });

        // Sans ce garde, on afficherait « jusqu'à Invalid Date » aux visiteurs.
        expect(composant.untilLabel()).toBe('');
      }
    );
  });

  describe('rendu serveur', () => {
    it('ne declenche aucune requete pendant le prerendu', () => {
      const { composant, get } = creer({ active: true, message: 'm' }, 'server');

      // Un fetch pendant le prerendu figerait l'etat du bandeau dans le HTML
      // statique — or il est justement concu pour changer sans rebuild.
      expect(get).not.toHaveBeenCalled();
      expect(composant.visible()).toBe(false);
    });
  });
});
