import { describe, it, expect, beforeEach } from 'vitest';
import { DOCUMENT, Injector, runInInjectionContext } from '@angular/core';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { Subject } from 'rxjs';

import { DonneesStructureesService } from './donnees-structurees.service';

/**
 * CE QUE CES TESTS DEFENDENT : le bloc JSON-LD decrit LA PAGE AFFICHEE, et
 * seulement elle.
 *
 * LE RISQUE PROPRE A UNE APPLICATION D'UNE SEULE PAGE : un bloc pose puis
 * oublie SUIT le visiteur. La FAQ du RSSI externalise se retrouverait declaree
 * a Google sur la page de tarifs, puis sur les mentions legales. Declarer a un
 * moteur un contenu que la page ne porte pas est precisement ce que ses
 * consignes qualifient de trompeur.
 */

const questions = [
  { question: 'Une question ?', answer: 'Une reponse.' },
  { question: 'Une autre ?', answer: 'Une autre reponse.' },
];

describe('DonneesStructureesService', () => {
  let service: DonneesStructureesService;
  let evenements: Subject<NavigationStart | NavigationEnd>;

  const blocs = () =>
    Array.from(document.head.querySelectorAll('script[data-jsonld-page]')) as HTMLScriptElement[];

  beforeEach(() => {
    document.head.innerHTML = '';
    evenements = new Subject();
    const injector = Injector.create({
      providers: [
        { provide: DOCUMENT, useValue: document },
        { provide: Router, useValue: { events: evenements.asObservable() } },
      ],
    });
    service = runInInjectionContext(injector, () => new DonneesStructureesService());
  });

  it('pose une FAQPage contenant les questions de la page', () => {
    service.poserFaq(questions);

    expect(blocs()).toHaveLength(1);
    const donnees = JSON.parse(blocs()[0].textContent ?? '{}');
    expect(donnees['@type']).toBe('FAQPage');
    expect(donnees.mainEntity).toHaveLength(2);
    expect(donnees.mainEntity[0].name).toBe('Une question ?');
    expect(donnees.mainEntity[0].acceptedAnswer.text).toBe('Une reponse.');
  });

  it('ne pose RIEN quand la page n’a aucune question', () => {
    // Un `FAQPage` vide est un signal trompeur, pas une absence.
    service.poserFaq([]);

    expect(blocs()).toHaveLength(0);
  });

  it('retire le bloc des le debut d’une navigation', () => {
    // LE TEST QUI COMPTE : sans lui, la FAQ suivrait le visiteur de page en page.
    service.poserFaq(questions);
    evenements.next(new NavigationStart(1, '/autre-page'));

    expect(blocs()).toHaveLength(0);
  });

  it('remplace le bloc au lieu de les empiler', () => {
    service.poserFaq(questions);
    service.poserFaq([{ question: 'Seule.', answer: 'Seule.' }]);

    expect(blocs()).toHaveLength(1);
    expect(JSON.parse(blocs()[0].textContent ?? '{}').mainEntity).toHaveLength(1);
  });

  it('ne touche pas au bloc statique d’index.html', () => {
    // Celui-ci decrit le service dans son ensemble et doit survivre a tout.
    document.head.innerHTML =
      '<script type="application/ld+json">{"@type":"SoftwareApplication"}</script>';

    service.poserFaq(questions);
    evenements.next(new NavigationStart(1, '/autre-page'));

    const restants = document.head.querySelectorAll('script[type="application/ld+json"]');
    expect(restants).toHaveLength(1);
    expect(restants[0].textContent).toContain('SoftwareApplication');
  });
});
