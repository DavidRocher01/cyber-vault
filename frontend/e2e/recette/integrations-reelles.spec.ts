import { test, expect, APIRequestContext } from '@playwright/test';

/**
 * Recette post-prod — LES INTEGRATIONS REELLES, celles qu'aucun test ne touche
 * ailleurs.
 *
 * POURQUOI CE FICHIER EXISTE. Le 2026-08-10, un rangement de rapports sur S3 a
 * failli partir avec un prefixe HORS DU DROIT ACCORDE au role de tache :
 *
 *     Autorise : cybervault-rssi-deliverables-prod/rssi-deliverables/*
 *     Ecrit    : rapports/*
 *
 * Chaque scan aurait echoue en production sur un AccessDenied — et AUCUN TEST
 * N'AURAIT PU LE VOIR. Les 2600 tests backend passent par le repli disque, qui
 * ne connait ni S3 ni IAM. Le defaut n'a ete trouve qu'en allant lire la
 * politique a la main.
 *
 * CE QUE CE FICHIER COUVRE, ET CE QU'IL NE COUVRE PAS.
 *
 * Le DEPOT d'une piece justificative — ecriture S3 sous le prefixe reellement
 * autorise, etiquetage GuardDuty, relecture du verdict, retrait — n'etait
 * exerce NULLE PART. Aucun des dix tests de recette API n'y touche.
 *
 * Le TELECHARGEMENT D'UN RAPPORT, lui, l'etait deja :
 * `backend/recette/test_06_site_scan.py` enregistre un site, lance un scan et,
 * s'il aboutit, telecharge le PDF. Un test de plus ici a d'abord ete ecrit, puis
 * RETIRE : il faisait doublon et ne pouvait structurellement pas passer, `test_06`
 * supprimant son site a la fin de chaque passage.
 *
 * CE QUI RESTE NON COUVERT PAR LA RECETTE, ET IL FAUT LE DIRE : le
 * telechargement d'un VIEUX rapport, dont le fichier a disparu et qu'il faut
 * refabriquer. C'est le cas qui a produit le 500 du 2026-08-09, et `test_06` ne
 * le voit pas non plus — il telecharge un rapport qu'il vient de creer, encore
 * present sur le disque de la tache courante. Ce chemin est garde par des tests
 * unitaires ; l'exercer en recette supposerait un vieux scan persistant, que le
 * compte canari n'a pas et ne doit pas avoir.
 *
 * ON NETTOIE CE QU'ON CREE. Le depot de test est retire dans tous les cas, y
 * compris en echec : une recette qui laisse des traces devient une source de
 * bruit, puis on cesse de la lire.
 */

const EMAIL = process.env['RECETTE_EMAIL'] || '';
const PASSWORD = process.env['RECETTE_PASSWORD'] || '';
const AVEC_CANARI = Boolean(EMAIL && PASSWORD);

const API = '/api/v1';

/** Un critere REEL du catalogue NIS2 (`nis2_catalogue.py`), pas un identifiant
 *  invente : le backend repond 422 sur un identifiant inconnu, et le test
 *  echouerait pour la mauvaise raison. */
const CRITERE = 'rssi';

/** Jeton du compte canari, ou `null` si l'authentification echoue. */
async function connecter(request: APIRequestContext): Promise<string | null> {
  const r = await request.post(`${API}/auth/login`, {
    data: { email: EMAIL, password: PASSWORD },
  });
  if (!r.ok()) return null;
  const corps = await r.json();
  return corps.access_token ?? null;
}

test.describe('Recette prod — integrations reelles', () => {
  test.describe.configure({ timeout: 120_000 });

  let entetes: Record<string, string>;

  test.beforeEach(async ({ request }) => {
    test.skip(!AVEC_CANARI, 'RECETTE_EMAIL / RECETTE_PASSWORD absents');
    const jeton = await connecter(request);
    expect(jeton, 'authentification du compte canari impossible').toBeTruthy();
    entetes = { Authorization: `Bearer ${jeton}` };
  });

  test('un fichier depose est ecrit, analyse, puis retire', async ({ request }) => {
    // LA CHAINE QUE PERSONNE N'AVAIT JAMAIS EXERCEE POUR DE VRAI : ecriture S3
    // sous le prefixe reellement autorise, etiquetage GuardDuty, relecture du
    // verdict. C'est ici qu'un droit IAM mal cadre se voit.
    const depot = await request.post(`${API}/nis2/me/criteres/${CRITERE}/pieces`, {
      headers: entetes,
      multipart: {
        fichier: {
          // UN PDF MINIMAL, ET C'EST OBLIGATOIRE. Le depot n'accepte que PDF,
          // Word, Excel, OpenDocument et images, ET verifie que les premiers
          // octets correspondent a l'extension annoncee. Un `.txt` est refuse
          // en 422 — c'est l'erreur qui a fait echouer cette recette au
          // 2026-08-10 et provoque le retour arriere d'un deploiement sain.
          name: 'recette-post-prod.pdf',
          mimeType: 'application/pdf',
          buffer: Buffer.from('%PDF-1.4\n% recette post-prod, supprime aussitot\n'),
        },
      },
    });

    // Le depot est reserve aux plans payants : un refus explicite n'est pas une
    // panne, mais on le DIT plutot que de passer en silence.
    test.skip(
      depot.status() === 402 || depot.status() === 403,
      `depot refuse (${depot.status()}) — le compte canari n’a pas de plan payant`
    );

    expect(
      depot.status(),
      `depot : ${depot.status()} — 422 = fichier refuse (type/signature/quota), 500 = droit S3 probablement mal cadre`
    ).toBe(201);

    const piece = await depot.json();
    expect(piece.id, 'le depot n’a pas renvoye d’identifiant').toBeTruthy();

    try {
      // Le verdict antivirus arrive en 20 a 45 s (mesure du 2026-08-05). On
      // attend un ETAT STABLE, sans exiger qu'il soit sain : un verdict
      // `indetermine` reste un verdict, et la chaine a fonctionne.
      let statut = piece.statut_analyse;
      for (let i = 0; i < 20 && statut === 'en_analyse'; i++) {
        await new Promise(r => setTimeout(r, 3000));
        const liste = await request.get(`${API}/nis2/me/pieces`, { headers: entetes });
        expect(liste.ok(), `GET /nis2/me/pieces a repondu ${liste.status()}`).toBeTruthy();
        const parCritere = await liste.json();
        const trouvee = Object.values(parCritere)
          .flat()
          .find((p: unknown) => (p as { id: number }).id === piece.id) as
          | { statut_analyse: string }
          | undefined;
        if (!trouvee) break;
        statut = trouvee.statut_analyse;
      }

      expect(
        statut,
        'le fichier est reste en analyse : la chaine GuardDuty ne rend plus de verdict'
      ).not.toBe('en_analyse');
    } finally {
      // Dans tous les cas, y compris en echec.
      await request
        .delete(`${API}/nis2/me/pieces/${piece.id}`, { headers: entetes })
        .catch(() => undefined);
    }
  });
});
