import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import { installerRepriseSaisie } from './reprise-saisie';

/**
 * CE QUE CES TESTS DEFENDENT : ce que l'utilisateur a tape avant l'hydratation
 * lui est RENDU, et ce qu'il a efface lui-meme ne revient pas.
 *
 * POURQUOI ILS EXISTENT. Ma premiere version s'arretait des que la liste des
 * champs suivis etait vide — donc au premier battement quand personne n'avait
 * encore tape, emportant l'ecouteur avec elle. Selon que la frappe precedait ou
 * suivait le demarrage du bundle, on perdait l'un ou l'autre cas, et le harnais
 * de bout en bout echouait PAREIL dans les deux : impossible d'y lire la cause.
 * Ces tests separent les deux chemins.
 */

/** Simule l'ecriture d'Angular a l'hydratation : la valeur du `FormControl`
 *  (vide) est poussee dans le champ, sans evenement. */
function hydratationEfface(champ: HTMLInputElement) {
  champ.value = '';
}

describe('installerRepriseSaisie', () => {
  let champ: HTMLInputElement;
  let arreter: () => void;
  let evenements: string[];

  beforeEach(() => {
    vi.useFakeTimers();
    document.body.innerHTML = '<input id="c" type="text" />';
    champ = document.getElementById('c') as HTMLInputElement;
    evenements = [];
    for (const type of ['input', 'change']) {
      champ.addEventListener(type, () => evenements.push(type));
    }
  });

  afterEach(() => {
    arreter?.();
    vi.useRealTimers();
  });

  it('rend la saisie faite AVANT l’installation', () => {
    // Le cas le plus frequent : le bundle pese pres d'un mega-octet, donc la
    // page est visible — et remplissable — bien avant qu'il ne demarre.
    champ.value = 'tape@avant.fr';

    arreter = installerRepriseSaisie(document, window);
    hydratationEfface(champ);
    vi.advanceTimersByTime(200);

    expect(champ.value).toBe('tape@avant.fr');
    expect(evenements).toContain('input');
    expect(evenements).toContain('change');
  });

  it('rend la saisie faite APRES l’installation', () => {
    arreter = installerRepriseSaisie(document, window);

    // Un premier battement a lieu sans que rien n'ait ete tape : c'est
    // exactement la ou la premiere version se coupait.
    vi.advanceTimersByTime(300);

    champ.value = 'tape@apres.fr';
    champ.dispatchEvent(new Event('input', { bubbles: true }));
    hydratationEfface(champ);
    vi.advanceTimersByTime(200);

    expect(champ.value).toBe('tape@apres.fr');
  });

  it('ne ressuscite pas un champ que l’utilisateur a vide lui-meme', () => {
    // Sa frappe est notee comme les autres : effacer EST une saisie.
    arreter = installerRepriseSaisie(document, window);
    champ.value = 'une erreur';
    champ.dispatchEvent(new Event('input', { bubbles: true }));
    champ.value = '';
    champ.dispatchEvent(new Event('input', { bubbles: true }));

    vi.advanceTimersByTime(500);

    expect(champ.value).toBe('');
  });

  it('ignore un champ pre-rempli par le serveur', () => {
    // `defaultValue` reflete l'attribut rendu : sans ecart, aucune frappe.
    champ.setAttribute('value', 'valeur du serveur');
    champ.value = 'valeur du serveur';

    arreter = installerRepriseSaisie(document, window);
    hydratationEfface(champ);
    vi.advanceTimersByTime(500);

    // On n'a rien remis : c'est l'application qui decide de ce champ.
    expect(champ.value).toBe('');
  });

  it('cesse de surveiller au bout de la fenetre', () => {
    // Une surveillance sans fin serait une fuite sur une page longue duree.
    champ.value = 'tape@avant.fr';
    arreter = installerRepriseSaisie(document, window);

    vi.advanceTimersByTime(10_000);
    champ.value = 'autre chose';
    champ.dispatchEvent(new Event('input', { bubbles: true }));
    hydratationEfface(champ);
    vi.advanceTimersByTime(500);

    expect(champ.value).toBe('');
  });
});
