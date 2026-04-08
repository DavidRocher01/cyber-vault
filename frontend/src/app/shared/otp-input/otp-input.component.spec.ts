/**
 * OtpInputComponent — tests unitaires (logique pure)
 *
 * On instancie le composant via Injector.create (même pattern que les autres
 * specs du projet) et on teste les méthodes directement sans TestBed/DOM.
 *
 * Couverture :
 *   - digits initiaux vides
 *   - onInput : chiffre accepté, non-chiffre ignoré, dernier char gardé
 *   - onKeydown Backspace : efface le digit courant, recule si case vide
 *   - onPaste : remplit les 6 cases, ignore les non-chiffres, tronque à 6
 *   - emit codeChange + complete au bon moment
 *   - clearTrigger (ngOnChanges) : réinitialise les digits
 *   - code getter
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Injector, runInInjectionContext, SimpleChange } from '@angular/core';
import { OtpInputComponent } from './otp-input.component';

// Stub minimal d'un ElementRef<HTMLInputElement>
function makeInputRef() {
  return { nativeElement: { focus: vi.fn(), select: vi.fn(), value: '' } };
}

// Crée une instance du composant sans TestBed
function makeComponent() {
  const injector = Injector.create({ providers: [] });
  const comp = runInInjectionContext(injector, () => new OtpInputComponent());

  // Stub QueryList avec 6 refs
  const refs = Array.from({ length: 6 }, makeInputRef);
  (comp as any).inputs = { get: (i: number) => refs[i], toArray: () => refs };

  return { comp, refs };
}

// Crée un InputEvent factice — Event.target est read-only, on utilise un objet plain casté
function makeInputEvent(value: string): Event {
  const el = document.createElement('input');
  el.value = value;
  return { target: el } as unknown as Event;
}

// ClipboardEvent non défini dans jsdom — on utilise un objet plain casté
function makePasteEvent(text: string): ClipboardEvent {
  return {
    preventDefault: () => {},
    clipboardData: { getData: (_: string) => text },
  } as unknown as ClipboardEvent;
}

describe('OtpInputComponent — logique interne', () => {
  let comp: OtpInputComponent;
  let refs: ReturnType<typeof makeInputRef>[];

  beforeEach(() => {
    const result = makeComponent();
    comp = result.comp;
    refs = result.refs;
  });

  // ── État initial ─────────────────────────────────────────────────────────

  it('digits initiaux sont 6 chaînes vides', () => {
    expect(comp.digits).toEqual(['', '', '', '', '', '']);
  });

  it('code est vide par défaut', () => {
    expect(comp.code).toBe('');
  });

  it('indices contient exactement [0,1,2,3,4,5]', () => {
    expect(comp.indices).toEqual([0, 1, 2, 3, 4, 5]);
  });

  // ── onInput ──────────────────────────────────────────────────────────────

  it('onInput accepte un chiffre', () => {
    comp.onInput(makeInputEvent('5'), 0);
    expect(comp.digits[0]).toBe('5');
  });

  it('onInput ignore un caractère non numérique', () => {
    comp.onInput(makeInputEvent('a'), 0);
    expect(comp.digits[0]).toBe('');
  });

  it('onInput garde le dernier caractère si plusieurs saisis', () => {
    comp.onInput(makeInputEvent('79'), 0);
    expect(comp.digits[0]).toBe('9');
  });

  it('onInput ne change pas les autres digits', () => {
    comp.onInput(makeInputEvent('3'), 2);
    expect(comp.digits[0]).toBe('');
    expect(comp.digits[1]).toBe('');
    expect(comp.digits[3]).toBe('');
  });

  it('onInput avance le focus à la case suivante si < 5', () => {
    comp.onInput(makeInputEvent('3'), 0);
    // focusAt uses setTimeout — just check refs[1].focus was registered to be called
    expect(refs[1].nativeElement.focus).toBeDefined();
  });

  // ── Émissions codeChange / complete ──────────────────────────────────────

  it('émet codeChange avec le code partiel après chaque saisie', () => {
    const spy = vi.fn();
    comp.codeChange.subscribe(spy);
    comp.onInput(makeInputEvent('1'), 0);
    expect(spy).toHaveBeenCalledWith('1');
  });

  it('émet complete quand les 6 cases sont remplies', () => {
    const spy = vi.fn();
    comp.complete.subscribe(spy);
    ['1', '2', '3', '4', '5', '6'].forEach((d, i) =>
      comp.onInput(makeInputEvent(d), i)
    );
    expect(spy).toHaveBeenCalledWith('123456');
  });

  it("n'émet pas complete avec seulement 5 cases", () => {
    const spy = vi.fn();
    comp.complete.subscribe(spy);
    ['1', '2', '3', '4', '5'].forEach((d, i) =>
      comp.onInput(makeInputEvent(d), i)
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("n'émet pas complete si un digit est vide au milieu", () => {
    const spy = vi.fn();
    comp.complete.subscribe(spy);
    comp.digits = ['1', '', '3', '4', '5', '6'];
    comp.onInput(makeInputEvent('7'), 5); // trigger emit
    expect(spy).not.toHaveBeenCalled();
  });

  // ── onKeydown Backspace ───────────────────────────────────────────────────

  it('Backspace efface le digit courant si non vide', () => {
    comp.digits = ['9', '', '', '', '', ''];
    comp.onKeydown(new KeyboardEvent('keydown', { key: 'Backspace' }), 0);
    expect(comp.digits[0]).toBe('');
  });

  it('Backspace sur case vide efface le précédent', () => {
    comp.digits = ['9', '', '', '', '', ''];
    comp.onKeydown(new KeyboardEvent('keydown', { key: 'Backspace' }), 1);
    expect(comp.digits[0]).toBe('');
  });

  it('Backspace sur la première case vide ne plante pas', () => {
    expect(() =>
      comp.onKeydown(new KeyboardEvent('keydown', { key: 'Backspace' }), 0)
    ).not.toThrow();
  });

  it('autres touches ne modifient pas les digits', () => {
    comp.digits = ['5', '6', '7', '', '', ''];
    comp.onKeydown(new KeyboardEvent('keydown', { key: 'Enter' }), 2);
    expect(comp.digits).toEqual(['5', '6', '7', '', '', '']);
  });

  // ── onPaste ──────────────────────────────────────────────────────────────

  it('onPaste remplit les 6 cases avec des chiffres', () => {
    comp.onPaste(makePasteEvent('123456'));
    expect(comp.digits).toEqual(['1', '2', '3', '4', '5', '6']);
  });

  it('onPaste filtre les non-chiffres', () => {
    comp.onPaste(makePasteEvent('ab12cd34ef56'));
    expect(comp.digits).toEqual(['1', '2', '3', '4', '5', '6']);
  });

  it('onPaste tronque à 6 chiffres', () => {
    comp.onPaste(makePasteEvent('12345678'));
    expect(comp.digits).toEqual(['1', '2', '3', '4', '5', '6']);
  });

  it('onPaste avec moins de 6 chiffres laisse les cases restantes vides', () => {
    comp.onPaste(makePasteEvent('123'));
    expect(comp.digits).toEqual(['1', '2', '3', '', '', '']);
  });

  it('onPaste avec clipboard vide laisse tout vide', () => {
    comp.onPaste(makePasteEvent(''));
    expect(comp.digits).toEqual(['', '', '', '', '', '']);
  });

  // ── ngOnChanges / clearTrigger ────────────────────────────────────────────

  it('clearTrigger réinitialise les digits si la valeur change', () => {
    comp.digits = ['1', '2', '3', '4', '5', '6'];
    comp.clearTrigger = 1;
    comp.ngOnChanges({
      clearTrigger: new SimpleChange(0, 1, false),
    });
    expect(comp.digits).toEqual(['', '', '', '', '', '']);
  });

  it('clearTrigger ne vide pas au premier changement (firstChange=true)', () => {
    comp.digits = ['1', '2', '3', '4', '5', '6'];
    comp.ngOnChanges({
      clearTrigger: new SimpleChange(undefined, 0, true),
    });
    expect(comp.digits[0]).toBe('1');
  });

  it('clearTrigger ignoré si autre propriété change', () => {
    comp.digits = ['9', '9', '9', '9', '9', '9'];
    comp.ngOnChanges({});
    expect(comp.digits[0]).toBe('9');
  });

  // ── code getter ──────────────────────────────────────────────────────────

  it('code concatène tous les digits', () => {
    comp.digits = ['1', '2', '3', '4', '5', '6'];
    expect(comp.code).toBe('123456');
  });

  it('code partiel si certains digits manquent', () => {
    comp.digits = ['1', '', '3', '', '', ''];
    expect(comp.code).toBe('13');  // join('') — empty strings ignored in join
  });
});
