import { describe, it, expect } from 'vitest';

import { cibler, genererFonction } from './routage-cloudfront';

/**
 * CE QUE CES TESTS PROTÈGENT. Cette fonction décide de la cible de CHAQUE
 * requête du site. Une erreur ici ne casse pas une page : elle les casse toutes,
 * et le rollback automatique du déploiement ne couvre pas le frontend.
 *
 * Ils exercent donc le code RÉELLEMENT ÉMIS, pas seulement la logique de
 * référence : la fonction publiée sur CloudFront est du JavaScript généré, et
 * c'est lui qui sera exécuté.
 */

const PRERENDUES = ['/', '/nis2', '/iso27001', '/blog', '/rssi-externalise'];

/** Exécute la fonction générée telle qu'elle sera publiée. */
function executer(uri: string, host = 'rochercybersecurite.com') {
  const source = genererFonction(PRERENDUES);
  const fabrique = new Function(`${source}; return handler;`) as () => (e: unknown) => {
    uri?: string;
    statusCode?: number;
    headers?: Record<string, { value: string }>;
  };
  return fabrique()({ request: { uri, headers: { host: { value: host } }, querystring: {} } });
}

describe('cibler() — la décision de routage', () => {
  it('sert son propre fichier à une route prérendue', () => {
    expect(cibler('/nis2', PRERENDUES)).toBe('/nis2/index.html');
    expect(cibler('/rssi-externalise', PRERENDUES)).toBe('/rssi-externalise/index.html');
  });

  it('traite la racine à part — sinon on produirait `//index.html`', () => {
    expect(cibler('/', PRERENDUES)).toBe('/index.html');
  });

  it('ignore la barre oblique finale : `/nis2/` et `/nis2` sont la même page', () => {
    expect(cibler('/nis2/', PRERENDUES)).toBe('/nis2/index.html');
  });

  it('RETOMBE SUR index.html pour tout le reste — c’est ce qui rend le changement sûr', () => {
    // Route rendue dans le navigateur, faute de frappe, URL inventée : toutes
    // gardent le comportement d'avant. On n'aiguille que vers des fichiers dont
    // la construction a attesté l'existence.
    expect(cibler('/blog/mon-article', PRERENDUES)).toBe('/index.html');
    expect(cibler('/nis22', PRERENDUES)).toBe('/index.html');
    expect(cibler('/page-qui-nexiste-pas', PRERENDUES)).toBe('/index.html');
  });

  it('laisse S3 servir les fichiers réels', () => {
    expect(cibler('/main-ABC123.js', PRERENDUES)).toBeNull();
    expect(cibler('/assets/logo.png', PRERENDUES)).toBeNull();
    expect(cibler('/robots.txt', PRERENDUES)).toBeNull();
    expect(cibler('/sitemap.xml', PRERENDUES)).toBeNull();
  });

  it('ne touche jamais à l’API', () => {
    expect(cibler('/api/v1/health', PRERENDUES)).toBeNull();
    expect(cibler('/api/v1/nis2/me', PRERENDUES)).toBeNull();
  });
});

describe('la fonction générée, exécutée telle qu’elle sera publiée', () => {
  it('aiguille une route prérendue vers son fichier', () => {
    expect(executer('/nis2').uri).toBe('/nis2/index.html');
  });

  it('laisse les fichiers réels intacts', () => {
    expect(executer('/main-ABC.js').uri).toBe('/main-ABC.js');
  });

  it('retombe sur index.html pour une URL inconnue', () => {
    expect(executer('/inconnue').uri).toBe('/index.html');
  });

  it('ne réécrit pas les chemins d’API', () => {
    expect(executer('/api/v1/health').uri).toBe('/api/v1/health');
  });

  it('redirige encore l’ancien domaine en 301', () => {
    // Comportement historique : le perdre casserait les liens entrants.
    const r = executer('/nis2', 'cyberscanapp.com');
    expect(r.statusCode).toBe(301);
    expect(r.headers?.['location'].value).toBe('https://rochercybersecurite.com/nis2');
  });

  it('reste sous la limite de taille de CloudFront', () => {
    // 10 Ko par fonction. Avec 61 routes on en est loin, mais une liste qui
    // grossirait sans limite finirait par faire echouer la publication —
    // apres le deploiement, quand il est trop tard.
    const taille = new TextEncoder().encode(genererFonction(PRERENDUES)).length;
    expect(taille).toBeLessThan(10_000);
  });

  it('n’embarque pas la racine dans la liste', () => {
    // `/` y figurerait produirait `//index.html`, servi par personne.
    expect(genererFonction(PRERENDUES)).not.toContain('"/"');
  });
});
