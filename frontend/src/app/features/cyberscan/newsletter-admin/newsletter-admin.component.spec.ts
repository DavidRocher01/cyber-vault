import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { FormArray, FormBuilder } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { NewsletterAdminComponent } from './newsletter-admin.component';

const STATS = { total: 10, active: 8, pending_confirmation: 2 };
const ARTICLES = [
  { position: 1, actu_title: 'Titre 1', actu_url: 'https://a.com', actu_source: 'Source A', reflex: 'Note 1', image_url: null },
  { position: 2, actu_title: 'Titre 2', actu_url: 'https://b.com', actu_source: 'Source B', reflex: 'Note 2', image_url: null },
];

function make() {
  const comp = Object.create(NewsletterAdminComponent.prototype) as NewsletterAdminComponent;
  (comp as any).apiKeySet      = signal(false);
  (comp as any).keyError       = signal(false);
  (comp as any).stats          = signal(null);
  (comp as any).sending        = signal(false);
  (comp as any).savingSchedule = signal(false);
  (comp as any).saveOk         = signal(false);
  (comp as any).sendResult     = signal(null);
  (comp as any).keyInput       = '';
  (comp as any).editionNumber  = 1;
  const fb = new FormBuilder();
  (comp as any).fb = fb;
  const slot = (pos: number) => fb.group({
    position:    [pos],
    actu_source: ['x'],
    actu_title:  ['x'],
    actu_url:    ['x'],
    reflex:      ['x'],
    image_url:   [null],
  });
  (comp as any).scheduleForm = fb.group({
    articles: fb.array(Array.from({ length: 6 }, (_, i) => slot(i + 1))),
  });
  return comp;
}

describe('NewsletterAdminComponent — submitKey()', () => {
  it('active apiKeySet et charge stats si clé valide', () => {
    const comp = make();
    (comp as any).keyInput = 'valid';
    (comp as any).http = {
      get: vi.fn((url: string) => url.includes('stats') ? of(STATS) : of([])),
    };
    comp.submitKey();
    expect(comp.apiKeySet()).toBe(true);
    expect(comp.stats()).toEqual(STATS);
  });

  it('affiche keyError si clé invalide', () => {
    const comp = make();
    (comp as any).http = { get: vi.fn().mockReturnValue(throwError(() => new Error('403'))) };
    comp.submitKey();
    expect(comp.keyError()).toBe(true);
    expect(comp.apiKeySet()).toBe(false);
  });
});

describe('NewsletterAdminComponent — loadSchedule()', () => {
  it('pré-remplit les slots avec les articles existants', () => {
    const comp = make();
    (comp as any).http = { get: vi.fn().mockReturnValue(of(ARTICLES)) };
    comp.loadSchedule();
    const arr = (comp as any).scheduleForm.get('articles') as FormArray;
    expect(arr.at(0).value.actu_title).toBe('Titre 1');
    expect(arr.at(1).value.actu_source).toBe('Source B');
  });

  it('laisse les slots vides pour les positions sans article', () => {
    const comp = make();
    (comp as any).http = { get: vi.fn().mockReturnValue(of([])) };
    comp.loadSchedule();
    const arr = (comp as any).scheduleForm.get('articles') as FormArray;
    expect(arr.at(0).value.actu_title).toBe('');
  });
});

describe('NewsletterAdminComponent — saveSchedule()', () => {
  it('envoie uniquement les slots remplis', () => {
    const comp = make();
    const putSpy = vi.fn().mockReturnValue(of([]));
    (comp as any).http = { put: putSpy };
    comp.saveSchedule();
    const body = putSpy.mock.calls[0][1];
    expect(body.length).toBe(6);
    expect(comp.saveOk()).toBe(true);
  });

  it('ignore les slots vides (champs tous vides)', () => {
    const comp = make();
    const arr = (comp as any).scheduleForm.get('articles') as FormArray;
    arr.at(2).patchValue({ actu_title: '', actu_url: '', actu_source: '', reflex: '' });
    const putSpy = vi.fn().mockReturnValue(of([]));
    (comp as any).http = { put: putSpy };
    comp.saveSchedule();
    const body = putSpy.mock.calls[0][1];
    expect(body.length).toBe(5);
    expect(body.every((a: any) => a.actu_title)).toBe(true);
  });
});

describe('NewsletterAdminComponent — sendFromSchedule()', () => {
  it('envoie et affiche le message de succès', () => {
    const comp = make();
    (comp as any).http = { post: vi.fn().mockReturnValue(of({ sent: 8, message: 'Édition #001 envoyée à 8 abonné(s).' })) };
    comp.sendFromSchedule();
    expect(comp.sendResult()?.ok).toBe(true);
  });

  it('affiche une erreur si le backend échoue', () => {
    const comp = make();
    (comp as any).http = { post: vi.fn().mockReturnValue(throwError(() => new Error('500'))) };
    comp.sendFromSchedule();
    expect(comp.sendResult()?.ok).toBe(false);
  });
});

describe('NewsletterAdminComponent — logout()', () => {
  it('remet tout à zéro', () => {
    const comp = make();
    (comp as any).apiKeySet.set(true);
    (comp as any).stats.set(STATS);
    comp.logout();
    expect(comp.apiKeySet()).toBe(false);
    expect(comp.stats()).toBeNull();
  });
});
