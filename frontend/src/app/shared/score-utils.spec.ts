/**
 * Tests des utilitaires de score — fonctions pures, 0 dépendance Angular.
 */
import { describe, it, expect } from 'vitest';
import { moduleScore, computeScore, getGrade, getScoreColor, getCategoryScores, RADAR_CATEGORIES } from './score-utils';

describe('moduleScore()', () => {
  it('retourne 100 pour OK', () => expect(moduleScore('OK')).toBe(100));
  it('retourne 50 pour WARNING', () => expect(moduleScore('WARNING')).toBe(50));
  it('retourne 0 pour CRITICAL', () => expect(moduleScore('CRITICAL')).toBe(0));
  it('retourne null pour null', () => expect(moduleScore(null)).toBeNull());
  it('retourne null pour undefined', () => expect(moduleScore(undefined)).toBeNull());
  it('retourne null pour une valeur inconnue', () => expect(moduleScore('UNKNOWN')).toBeNull());
});

describe('computeScore()', () => {
  it('retourne null si resultsJson est null', () => expect(computeScore(null)).toBeNull());
  it('retourne null si resultsJson est vide', () => expect(computeScore('')).toBeNull());
  it('retourne null si le JSON est invalide', () => expect(computeScore('not-json')).toBeNull());
  it('retourne null si aucun module connu n\'a de statut', () => {
    expect(computeScore(JSON.stringify({ unknown_module: { status: 'OK' } }))).toBeNull();
  });

  it('calcule un score pondéré correct pour un seul module', () => {
    const json = JSON.stringify({ ssl: { status: 'OK' } });
    expect(computeScore(json)).toBe(100);
  });

  it('calcule un score de 50 pour WARNING sur ssl', () => {
    const json = JSON.stringify({ ssl: { status: 'WARNING' } });
    expect(computeScore(json)).toBe(50);
  });

  it('calcule un score de 0 pour CRITICAL sur ssl', () => {
    const json = JSON.stringify({ ssl: { status: 'CRITICAL' } });
    expect(computeScore(json)).toBe(0);
  });

  it('ignore les modules sans statut valide dans la moyenne', () => {
    const json = JSON.stringify({
      ssl: { status: 'OK' },
      headers: {},  // empty → skipped
    });
    expect(computeScore(json)).toBe(100);
  });

  it('calcule un score mixte', () => {
    const json = JSON.stringify({
      ssl: { status: 'OK' },     // weight 3, score 100
      headers: { status: 'CRITICAL' }, // weight 3, score 0
    });
    const score = computeScore(json);
    expect(score).toBe(50); // (100*3 + 0*3) / 6 = 50
  });
});

describe('getGrade()', () => {
  it('retourne A pour >= 90', () => {
    expect(getGrade(100)).toBe('A');
    expect(getGrade(90)).toBe('A');
  });

  it('retourne B pour 75-89', () => {
    expect(getGrade(85)).toBe('B');
    expect(getGrade(75)).toBe('B');
  });

  it('retourne C pour 60-74', () => {
    expect(getGrade(70)).toBe('C');
    expect(getGrade(60)).toBe('C');
  });

  it('retourne D pour 40-59', () => {
    expect(getGrade(50)).toBe('D');
    expect(getGrade(40)).toBe('D');
  });

  it('retourne F pour < 40', () => {
    expect(getGrade(39)).toBe('F');
    expect(getGrade(0)).toBe('F');
  });
});

describe('getScoreColor()', () => {
  it('retourne vert pour >= 90', () => {
    expect(getScoreColor(90)).toBe('#4ade80');
    expect(getScoreColor(100)).toBe('#4ade80');
  });

  it('retourne lime pour 75-89', () => {
    expect(getScoreColor(75)).toBe('#a3e635');
    expect(getScoreColor(89)).toBe('#a3e635');
  });

  it('retourne jaune pour 60-74', () => {
    expect(getScoreColor(60)).toBe('#facc15');
    expect(getScoreColor(74)).toBe('#facc15');
  });

  it('retourne orange pour 40-59', () => {
    expect(getScoreColor(40)).toBe('#fb923c');
    expect(getScoreColor(59)).toBe('#fb923c');
  });

  it('retourne rouge pour < 40', () => {
    expect(getScoreColor(0)).toBe('#f87171');
    expect(getScoreColor(39)).toBe('#f87171');
  });
});

describe('getCategoryScores()', () => {
  it('retourne des zéros si resultsJson est null', () => {
    const scores = getCategoryScores(null);
    expect(scores.every(s => s === 0)).toBe(true);
  });

  it('retourne des zéros si le JSON est invalide', () => {
    const scores = getCategoryScores('not-json');
    expect(scores.every(s => s === 0)).toBe(true);
  });

  it('retourne un tableau de la même longueur que RADAR_CATEGORIES', () => {
    const scores = getCategoryScores(null);
    expect(scores.length).toBe(RADAR_CATEGORIES.length);
  });

  it('calcule 100 pour la catégorie SSL si ssl=OK et tls=OK', () => {
    const json = JSON.stringify({ ssl: { status: 'OK' }, tls: { status: 'OK' } });
    const scores = getCategoryScores(json);
    expect(scores[0]).toBe(100); // SSL/TLS est la première catégorie
  });

  it('calcule 50 pour la catégorie SSL si ssl=WARNING', () => {
    const json = JSON.stringify({ ssl: { status: 'WARNING' } });
    const scores = getCategoryScores(json);
    expect(scores[0]).toBe(50);
  });
});
