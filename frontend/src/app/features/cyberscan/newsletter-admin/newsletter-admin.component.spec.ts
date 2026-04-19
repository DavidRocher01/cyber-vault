import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { NewsletterAdminComponent } from './newsletter-admin.component';

const STATS = { total: 10, active: 8, pending_confirmation: 2 };
const ARTICLES = [
  { position: 1, actu_title: 'Titre 1', actu_url: 'https://a.com', actu_source: 'Source A', reflex: 'Note 1' },
  { position: 2, actu_title: 'Titre 2', actu_url: 'https://b.com', actu_source: 'Source B', reflex: 'Note 2' },
];

function make() {
  const comp = Object.create(NewsletterAdminComponent.prototype) as NewsletterAdminComponent;
  (comp as any).apiKeySet       = signal(false);
  (comp as any).keyError        = signal(false);
  (comp as any).stats           = signal(null);
  (comp as any).articles        = signal([]);
  (comp as any).sending         = signal(false);
  (comp as any).sendResult      = signal(null);
  (comp as any).editingPosition = signal(null);
  (comp as any).adding          = signal(false);
  (comp as any).keyInput        = '';
  (comp as any).editionNumber   = 1;
  const fb = new FormBuilder();
  (comp as any).fb = fb;
  (comp as any).articleForm = fb.nonNullable.group({
    position:    [1,   [Validators.required, Validators.min(1), Validators.max(6)]],
    actu_title:  ['x', Validators.required],
    actu_url:    ['x', Validators.required],
    actu_source: ['x', Validators.required],
    reflex:      ['x', Validators.required],
  });
  return comp;
}

describe('NewsletterAdminComponent — submitKey()', () => {
  it('active apiKeySet et charge stats + schedule si clé valide', () => {
    const comp = make();
    (comp as any).keyInput = 'valid';
    (comp as any).http = {
      get: vi.fn().mockReturnValue(of(STATS)),
    };
    comp.submitKey();
    expect(comp.apiKeySet()).toBe(true);
    expect(comp.stats()).toEqual(STATS);
    expect(comp.keyError()).toBe(false);
  });

  it('affiche keyError si clé invalide', () => {
    const comp = make();
    (comp as any).http = { get: vi.fn().mockReturnValue(throwError(() => new Error('403'))) };
    comp.submitKey();
    expect(comp.keyError()).toBe(true);
    expect(comp.apiKeySet()).toBe(false);
  });
});

describe('NewsletterAdminComponent — gestion des articles', () => {
  it('startEdit peuple le formulaire avec les valeurs de l\'article', () => {
    const comp = make();
    comp.startEdit(ARTICLES[0]);
    expect(comp.articleForm.value.actu_title).toBe('Titre 1');
    expect(comp.editingPosition()).toBe(1);
    expect(comp.adding()).toBe(false);
  });

  it('startAdd initialise un formulaire vide avec la prochaine position', () => {
    const comp = make();
    (comp as any).articles.set(ARTICLES);
    comp.startAdd();
    expect(comp.adding()).toBe(true);
    expect(comp.articleForm.value.position).toBe(3);
  });

  it('cancelEdit remet editingPosition et adding à null/false', () => {
    const comp = make();
    (comp as any).editingPosition.set(1);
    (comp as any).adding.set(true);
    comp.cancelEdit();
    expect(comp.editingPosition()).toBeNull();
    expect(comp.adding()).toBe(false);
  });

  it('deleteArticle renumérote les positions restantes', () => {
    const comp = make();
    (comp as any).articles.set(ARTICLES);
    (comp as any).http = { put: vi.fn().mockReturnValue(of([{ position: 1, actu_title: 'Titre 2', actu_url: 'https://b.com', actu_source: 'Source B', reflex: 'Note 2' }])) };
    comp.deleteArticle(1);
    expect((comp as any).http.put).toHaveBeenCalledOnce();
    const body = (comp as any).http.put.mock.calls[0][1];
    expect(body[0].position).toBe(1);
    expect(body[0].actu_title).toBe('Titre 2');
  });
});

describe('NewsletterAdminComponent — sendFromSchedule()', () => {
  it('envoie l\'édition et affiche le message de succès', () => {
    const comp = make();
    (comp as any).articles.set(ARTICLES);
    (comp as any).http = { post: vi.fn().mockReturnValue(of({ sent: 8, message: 'Édition #001 envoyée à 8 abonné(s).' })) };
    comp.sendFromSchedule();
    expect(comp.sending()).toBe(false);
    expect(comp.sendResult()?.ok).toBe(true);
    expect(comp.sendResult()?.message).toContain('8');
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
    (comp as any).articles.set(ARTICLES);
    comp.logout();
    expect(comp.apiKeySet()).toBe(false);
    expect(comp.stats()).toBeNull();
    expect(comp.articles()).toEqual([]);
  });
});
