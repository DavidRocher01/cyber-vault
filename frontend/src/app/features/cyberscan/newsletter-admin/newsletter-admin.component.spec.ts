import { describe, it, expect, vi, beforeEach } from 'vitest';
import { signal } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { NewsletterAdminComponent } from './newsletter-admin.component';

const STATS = { total: 10, active: 8, pending_confirmation: 2 };

function make() {
  const comp = Object.create(NewsletterAdminComponent.prototype) as NewsletterAdminComponent;
  (comp as any).apiKeySet   = signal(false);
  (comp as any).keyError    = signal(false);
  (comp as any).stats       = signal(null);
  (comp as any).sending     = signal(false);
  (comp as any).sendResult  = signal(null);
  (comp as any).keyInput    = '';
  const fb = new FormBuilder();
  (comp as any).fb = fb;
  (comp as any).form = fb.nonNullable.group({
    edition:      [1,    Validators.required],
    flash_title:  ['x',  Validators.required],
    flash_body:   ['x',  Validators.required],
    reflex_title: ['x',  Validators.required],
    reflex_body:  ['x',  Validators.required],
    legal_title:  ['x',  Validators.required],
    legal_body:   ['x',  Validators.required],
  });
  return comp;
}

describe('NewsletterAdminComponent — submitKey()', () => {
  it('active apiKeySet et charge les stats si la clé est valide', () => {
    const comp = make();
    (comp as any).keyInput = 'valid-key';
    (comp as any).http = { get: vi.fn().mockReturnValue(of(STATS)) };
    comp.submitKey();
    expect(comp.apiKeySet()).toBe(true);
    expect(comp.stats()).toEqual(STATS);
    expect(comp.keyError()).toBe(false);
  });

  it('affiche keyError si la clé est invalide', () => {
    const comp = make();
    (comp as any).http = { get: vi.fn().mockReturnValue(throwError(() => new Error('403'))) };
    comp.submitKey();
    expect(comp.keyError()).toBe(true);
    expect(comp.apiKeySet()).toBe(false);
  });
});

describe('NewsletterAdminComponent — sendIssue()', () => {
  it('envoie le formulaire et affiche le message de succès', () => {
    const comp = make();
    (comp as any).http = {
      get:  vi.fn().mockReturnValue(of(STATS)),
      post: vi.fn().mockReturnValue(of({ sent: 8, message: 'Édition #001 envoyée à 8 abonné(s).' })),
    };
    comp.sendIssue();
    expect(comp.sending()).toBe(false);
    expect(comp.sendResult()?.ok).toBe(true);
    expect(comp.sendResult()?.message).toContain('8');
  });

  it('affiche une erreur si le backend échoue', () => {
    const comp = make();
    (comp as any).http = {
      get:  vi.fn().mockReturnValue(of(STATS)),
      post: vi.fn().mockReturnValue(throwError(() => new Error('500'))),
    };
    comp.sendIssue();
    expect(comp.sending()).toBe(false);
    expect(comp.sendResult()?.ok).toBe(false);
  });

  it('ne fait rien si le formulaire est invalide', () => {
    const comp = make();
    comp.form.controls.flash_title.setValue('');
    const postSpy = vi.fn();
    (comp as any).http = { post: postSpy };
    comp.sendIssue();
    expect(postSpy).not.toHaveBeenCalled();
  });
});

describe('NewsletterAdminComponent — logout()', () => {
  it('remet apiKeySet à false et vide les stats', () => {
    const comp = make();
    (comp as any).apiKeySet.set(true);
    (comp as any).stats.set(STATS);
    comp.logout();
    expect(comp.apiKeySet()).toBe(false);
    expect(comp.stats()).toBeNull();
  });
});
