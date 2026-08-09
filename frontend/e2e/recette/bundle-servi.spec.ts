import { test, expect } from '@playwright/test';

/**
 * CE QUE LE BUNDLE RÉELLEMENT SERVI CONTIENT.
 *
 * POURQUOI CE FICHIER EXISTE, ALORS QUE LA CI TESTE DÉJÀ LE GESTIONNAIRE. La CI
 * prouve qu'il fonctionne **dans le code source** ; elle ne prouve pas qu'il est
 * présent dans l'artefact **déployé**. L'écart est théorique — le build est
 * déterministe — mais c'est précisément le genre d'écart qui a produit les trois
 * défauts du 2026-08-07 : à chaque fois, ce que le code disait et ce que la
 * production faisait divergeaient.
 *
 * Ce test ne rejoue PAS la simulation de l'onglet périmé : elle vit en CI, où
 * elle bloque avant le déploiement plutôt que de déclencher un rollback après.
 * Ici on se contente de vérifier la PRÉSENCE, pour quelques secondes de porte de
 * rollback.
 *
 * SI CE TEST ÉCHOUE, la lecture est directe : un déploiement a livré un bundle
 * sans le garde-fou, et le prochain figera les onglets ouverts sans que personne
 * ne le sache avant qu'un utilisateur ne clique dans le vide.
 */

/** Marqueur posé en `sessionStorage` par le gestionnaire. Les littéraux de
 *  chaîne ne sont pas renommés à la minification — celui-ci traverse le build
 *  tel quel, et c'est ce qui en fait une sonde fiable. */
const MARQUEUR = 'rechargement-module-manquant';

/** Un des motifs de détection d'échec de chargement, propre au gestionnaire. */
const MOTIF = 'Failed to fetch dynamically imported module';

test('le bundle déployé embarque le garde-fou des onglets périmés', async ({ page, request }) => {
  await page.goto('/');
  const scripts = await page.$$eval('script[src]', els =>
    els.map(e => (e as HTMLScriptElement).getAttribute('src') || '').filter(Boolean)
  );

  expect(scripts.length, 'aucun script dans la page — le bundle est-il servi ?').toBeGreaterThan(0);

  let trouve = false;
  const inspectes: string[] = [];
  for (const src of scripts) {
    // Les scripts tiers (analytics) sont sur d'autres domaines : on ne lit que
    // les nôtres.
    if (/^https?:\/\//.test(src) && !src.includes(new URL(page.url()).host)) continue;
    const r = await request.get(src);
    if (!r.ok()) continue;
    inspectes.push(src);
    const corps = await r.text();
    if (corps.includes(MARQUEUR) && corps.includes(MOTIF)) {
      trouve = true;
      break;
    }
  }

  expect(
    trouve,
    `garde-fou absent du bundle servi (scripts inspectés : ${inspectes.join(', ')})`
  ).toBe(true);
});
