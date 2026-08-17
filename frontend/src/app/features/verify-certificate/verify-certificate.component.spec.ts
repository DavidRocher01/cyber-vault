import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { of, throwError } from 'rxjs';

import { VerifyCertificateComponent } from './verify-certificate.component';
import {
  AwarenessService,
  type CertificateVerification,
} from '../cyberscan/services/awareness.service';

/**
 * Page PUBLIQUE : n'importe qui recoit ce lien pour verifier une attestation de
 * sensibilisation. C'est la seule preuve qu'un employeur ou un auditeur peut
 * consulter, donc le seul ecran ou un faux « valide » couterait cher.
 *
 * La version precedente de ce spec construisait le composant par
 * `Object.create(prototype)`, ce qui contourne l'injection : `ngOnInit` n'etait
 * jamais appele et les quatre tests verifiaient qu'un signal retient ce qu'on
 * vient d'y ecrire. Couverture affichee, logique nue.
 */
const ATTESTATION: CertificateVerification = {
  valid: true,
  public_id: 'CERT-123',
  learner_name: 'Alice',
  program_title: 'NIS2 Fondamentaux',
  issued_at: '2026-01-01T00:00:00Z',
  expires_at: null,
  verification_count: 1,
};

function creer(options: {
  publicId?: string | null;
  token?: string | null;
  reponse?: CertificateVerification | 'erreur';
}) {
  const verifyCertificate = vi.fn(() =>
    options.reponse === 'erreur'
      ? throwError(() => new Error('introuvable'))
      : of(options.reponse ?? ATTESTATION)
  );

  const route = {
    snapshot: {
      paramMap: { get: () => options.publicId ?? null },
      queryParamMap: { get: () => options.token ?? null },
    },
  };

  const injector = Injector.create({
    providers: [
      { provide: AwarenessService, useValue: { verifyCertificate } },
      { provide: ActivatedRoute, useValue: route },
    ],
  });
  const composant = runInInjectionContext(injector, () => new VerifyCertificateComponent());
  composant.ngOnInit();
  return { composant, verifyCertificate };
}

describe('VerifyCertificateComponent', () => {
  describe('lien complet', () => {
    it('affiche l attestation renvoyee par le service', () => {
      const { composant, verifyCertificate } = creer({ publicId: 'CERT-123', token: 'jeton' });

      expect(verifyCertificate).toHaveBeenCalledWith('CERT-123', 'jeton');
      expect(composant.cert()?.public_id).toBe('CERT-123');
      expect(composant.cert()?.learner_name).toBe('Alice');
      expect(composant.loading()).toBe(false);
    });

    it('relaie une attestation invalide sans la maquiller', () => {
      const { composant } = creer({
        publicId: 'CERT-404',
        token: 'jeton',
        reponse: { ...ATTESTATION, valid: false },
      });

      // Le verdict vient du backend : le composant ne doit ni le corriger ni le
      // deviner. Un `valid: false` transforme en page rassurante serait le pire
      // defaut possible sur cet ecran.
      expect(composant.cert()?.valid).toBe(false);
      expect(composant.loading()).toBe(false);
    });
  });

  describe('lien incomplet', () => {
    it.each([
      ['sans identifiant', { publicId: null, token: 'jeton' }],
      ['sans jeton', { publicId: 'CERT-123', token: null }],
      ['sans rien', { publicId: null, token: null }],
    ])('%s : n interroge pas le backend et sort du chargement', (_titre, params) => {
      const { composant, verifyCertificate } = creer(params);

      // Interroger le backend avec une chaine vide produirait un appel inutile
      // sur une route publique — et un 404 presente comme une panne.
      expect(verifyCertificate).not.toHaveBeenCalled();
      expect(composant.cert()).toBeNull();
      expect(composant.loading()).toBe(false);
    });
  });

  describe('echec de la verification', () => {
    it('sort du chargement sans afficher d attestation', () => {
      const { composant } = creer({ publicId: 'CERT-123', token: 'faux', reponse: 'erreur' });

      // Sans ce `error:`, la page resterait bloquee sur son indicateur de
      // chargement : le visiteur n'apprendrait ni que c'est valide, ni que ca
      // ne l'est pas.
      expect(composant.loading()).toBe(false);
      expect(composant.cert()).toBeNull();
    });
  });
});
