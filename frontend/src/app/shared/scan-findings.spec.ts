/**
 * Tests des utilitaires scan-findings — fonctions pures, 0 dépendance Angular.
 */
import { describe, it, expect } from 'vitest';
import { extractSummary, getFindings, MODULE_META } from './scan-findings';

describe('extractSummary() — ssl', () => {
  it('affiche la durée de validité restante', () => {
    const result = extractSummary('ssl', { days_remaining: 30, status: 'OK' });
    expect(result.some(r => r.label === 'Expire dans' && r.value.includes('30'))).toBe(true);
  });

  it('affiche le protocole si présent', () => {
    const result = extractSummary('ssl', { protocol: 'TLSv1.3', status: 'OK' });
    expect(result.some(r => r.label === 'Protocole' && r.value === 'TLSv1.3')).toBe(true);
  });

  it('affiche Valide: Oui si valid=true', () => {
    const result = extractSummary('ssl', { valid: true, status: 'OK' });
    expect(result.some(r => r.label === 'Valide' && r.value === 'Oui')).toBe(true);
  });

  it('retourne tableau vide si données vides', () => {
    expect(extractSummary('ssl', {})).toEqual([]);
  });
});

describe('extractSummary() — headers', () => {
  it('liste les headers manquants', () => {
    const result = extractSummary('headers', { headers_missing: ['X-Frame-Options', 'CSP'], status: 'WARNING' });
    expect(result[0].label).toBe('Headers manquants');
    expect(result[0].value).toContain('X-Frame-Options');
  });

  it('indique Aucun si aucun header manquant', () => {
    const result = extractSummary('headers', { headers_missing: [], status: 'OK' });
    expect(result[0].value).toBe('Aucun');
  });

  it('limite à 4 headers manquants', () => {
    const missing = ['A', 'B', 'C', 'D', 'E'];
    const result = extractSummary('headers', { headers_missing: missing, status: 'WARNING' });
    expect(result[0].value.split(', ').length).toBeLessThanOrEqual(4);
  });
});

describe('extractSummary() — email', () => {
  it('inclut SPF, DKIM, DMARC', () => {
    const result = extractSummary('email', { spf: { found: true }, dkim: { found: false }, dmarc: { found: true }, status: 'WARNING' });
    expect(result.some(r => r.label === 'SPF')).toBe(true);
    expect(result.some(r => r.label === 'DKIM')).toBe(true);
    expect(result.some(r => r.label === 'DMARC')).toBe(true);
  });

  it('affiche "Présent" pour found: true', () => {
    const result = extractSummary('email', { spf: { found: true }, status: 'OK' });
    expect(result.find(r => r.label === 'SPF')?.value).toBe('Présent');
  });

  it('affiche "Absent" pour found: false', () => {
    const result = extractSummary('email', { dkim: { found: false }, status: 'CRITICAL' });
    expect(result.find(r => r.label === 'DKIM')?.value).toBe('Absent');
  });
});

describe('extractSummary() — cookies', () => {
  it('liste les problèmes si présents', () => {
    const result = extractSummary('cookies', { issues: ['HttpOnly manquant', 'Secure manquant'], status: 'WARNING' });
    expect(result[0].label).toBe('Problèmes');
  });

  it('indique config correcte si aucun problème', () => {
    const result = extractSummary('cookies', { issues: [], status: 'OK' });
    expect(result[0].value).toContain('correcte');
  });
});

describe('extractSummary() — cors', () => {
  it('affiche allow_origin si présent', () => {
    const result = extractSummary('cors', { allow_origin: '*', status: 'CRITICAL' });
    expect(result[0].label).toContain('Allow-Origin');
    expect(result[0].value).toBe('*');
  });

  it('indique en-tête absent si cors pas présent', () => {
    const result = extractSummary('cors', { status: 'OK' });
    expect(result[0].value).toContain('absent');
  });
});

describe('extractSummary() — ip', () => {
  it('affiche l\'IP et le nombre de blacklists', () => {
    const result = extractSummary('ip', { ip: '1.2.3.4', total_listed: 2, listed_in: ['Spamhaus', 'SORBS'], status: 'WARNING' });
    expect(result.some(r => r.label === 'IP')).toBe(true);
    expect(result.some(r => r.label === 'Blacklists')).toBe(true);
  });

  it('affiche les listes dans lesquelles l\'IP est référencée', () => {
    const result = extractSummary('ip', { ip: '1.2.3.4', total_listed: 1, listed_in: ['Spamhaus'], status: 'WARNING' });
    expect(result.some(r => r.label === 'Listé dans')).toBe(true);
  });

  it('n\'affiche pas les listes si listed_in est vide', () => {
    const result = extractSummary('ip', { ip: '1.2.3.4', total_listed: 0, listed_in: [], status: 'OK' });
    expect(result.some(r => r.label === 'Listé dans')).toBe(false);
  });
});

describe('extractSummary() — dns', () => {
  it('affiche le nombre de sous-domaines', () => {
    const result = extractSummary('dns', { found: [{ subdomain: 'api' }, { subdomain: 'mail' }], status: 'OK' });
    expect(result[0].value).toBe('2');
  });

  it('affiche "Aucun trouvé" si pas de sous-domaines', () => {
    const result = extractSummary('dns', { found: [], status: 'OK' });
    expect(result[0].value).toContain('Aucun');
  });
});

describe('extractSummary() — cms', () => {
  it('affiche le CMS si détecté', () => {
    const result = extractSummary('cms', { cms: 'WordPress', status: 'WARNING' });
    expect(result[0].value).toBe('WordPress');
  });

  it('affiche "Non détecté" si absent', () => {
    const result = extractSummary('cms', { status: 'OK' });
    expect(result[0].value).toContain('Non détecté');
  });
});

describe('extractSummary() — waf', () => {
  it('affiche le WAF si détecté', () => {
    const result = extractSummary('waf', { detected: true, waf_name: 'Cloudflare', status: 'OK' });
    expect(result[0].value).toBe('Cloudflare');
  });

  it('affiche "Non détecté" si absent', () => {
    const result = extractSummary('waf', { detected: false, status: 'OK' });
    expect(result[0].value).toContain('Non détecté');
  });
});

describe('extractSummary() — tech', () => {
  it('liste les technologies', () => {
    const result = extractSummary('tech', { technologies: ['React', 'Node.js'], status: 'OK' });
    expect(result[0].label).toBe('Technologies');
    expect(result[0].value).toContain('React');
  });

  it('retourne vide si pas de technologies', () => {
    expect(extractSummary('tech', { technologies: [], status: 'OK' })).toEqual([]);
  });
});

describe('extractSummary() — tls', () => {
  it('affiche les protocoles supportés', () => {
    const result = extractSummary('tls', { supported_protocols: ['TLSv1.2', 'TLSv1.3'], hsts: { present: true }, status: 'OK' });
    expect(result.some(r => r.label === 'Protocoles')).toBe(true);
    expect(result.some(r => r.label === 'HSTS')).toBe(true);
  });

  it('affiche HSTS désactivé si absent', () => {
    const result = extractSummary('tls', { supported_protocols: ['TLSv1.3'], hsts: { present: false }, status: 'OK' });
    const hsts = result.find(r => r.label === 'HSTS');
    expect(hsts?.value).toBe('Désactivé');
  });

  it('retourne vide si aucun protocole ni hsts', () => {
    const result = extractSummary('tls', { status: 'OK' });
    expect(result).toEqual([]);
  });
});

describe('extractSummary() — http_methods', () => {
  it('liste les méthodes dangereuses', () => {
    const result = extractSummary('http_methods', { dangerous_allowed: ['PUT', 'DELETE'], status: 'WARNING' });
    expect(result[0].value).toContain('PUT');
  });

  it('indique aucune méthode dangereuse', () => {
    const result = extractSummary('http_methods', { dangerous_allowed: [], status: 'OK' });
    expect(result[0].value).toContain('Aucune');
  });
});

describe('extractSummary() — jwt', () => {
  it('liste les problèmes JWT', () => {
    const result = extractSummary('jwt', { issues: ['alg: none autorisé'], status: 'CRITICAL' });
    expect(result[0].label).toContain('JWT');
  });

  it('indique aucun token détecté si pas de problèmes', () => {
    const result = extractSummary('jwt', { issues: [], status: 'OK' });
    expect(result[0].value).toContain('Aucun');
  });
});

describe('extractSummary() — fallback', () => {
  it('retourne les propriétés scalaires pour une clé inconnue', () => {
    const result = extractSummary('custom_module', { status: 'OK', value: 42, name: 'test' });
    expect(result.some(r => r.label === 'value')).toBe(true);
    expect(result.some(r => r.label === 'name')).toBe(true);
  });

  it('exclut la propriété status du fallback', () => {
    const result = extractSummary('other', { status: 'OK', note: 'hello' });
    expect(result.some(r => r.label === 'status')).toBe(false);
  });
});

describe('getFindings()', () => {
  it('retourne un tableau vide si resultsJson est null', () => {
    expect(getFindings(null)).toEqual([]);
  });

  it('retourne un tableau vide si JSON invalide', () => {
    expect(getFindings('not-json')).toEqual([]);
  });

  it('retourne un tableau de la même longueur que MODULE_META', () => {
    const json = JSON.stringify({ ssl: { status: 'OK' } });
    expect(getFindings(json).length).toBe(MODULE_META.length);
  });

  it('marque les modules hors tier comme skipped', () => {
    const json = JSON.stringify({ _meta: { tier: 1 }, tech: { status: 'OK' } });
    const findings = getFindings(json);
    const techFinding = findings.find(f => f.key === 'tech');
    expect(techFinding?.skipped).toBe(true);
  });

  it('ne marque pas comme skipped les modules du bon tier', () => {
    const json = JSON.stringify({ _meta: { tier: 2 }, ssl: { status: 'OK' } });
    const findings = getFindings(json);
    const sslFinding = findings.find(f => f.key === 'ssl');
    expect(sslFinding?.skipped).toBe(false);
    expect(sslFinding?.status).toBe('OK');
  });

  it('retourne status null pour les modules skipped', () => {
    const json = JSON.stringify({ _meta: { tier: 1 }, jwt: { status: 'OK' } });
    const findings = getFindings(json);
    const jwtFinding = findings.find(f => f.key === 'jwt');
    expect(jwtFinding?.status).toBeNull();
  });
});
