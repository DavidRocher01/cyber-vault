import { describe, it, expect, vi, beforeEach } from 'vitest';
import { signal } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { DarkwebDossierNewComponent } from './darkweb-dossier-new.component';

const DOMAIN_PATTERN = /^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;

function make(): DarkwebDossierNewComponent {
  const comp = Object.create(DarkwebDossierNewComponent.prototype) as DarkwebDossierNewComponent;
  comp.form = new FormGroup({
    company_name: new FormControl('', [
      Validators.required,
      Validators.minLength(2),
      Validators.maxLength(200),
    ]),
    domain: new FormControl('', [Validators.required, Validators.pattern(DOMAIN_PATTERN)]),
  });
  (comp as any).csvFile = signal<File | null>(null);
  (comp as any).csvError = signal<string | null>(null);
  (comp as any).emailPreview = signal<string[]>([]);
  (comp as any).submitting = signal(false);
  (comp as any).service = { create: vi.fn() };
  (comp as any).router = { navigate: vi.fn() };
  (comp as any).snack = { open: vi.fn() };
  return comp;
}

function setForm(comp: DarkwebDossierNewComponent, name: string, domain: string) {
  comp.form.setValue({ company_name: name, domain });
  comp.form.markAllAsTouched();
}

function makeFile(name = 'emails.csv', type = 'text/csv', size = 100): File {
  return new File(['email\njohn@acme.fr\n'], name, { type });
}

// ── canSubmit ─────────────────────────────────────────────────────────────────

describe('DarkwebDossierNewComponent — canSubmit', () => {
  it('false quand formulaire vide', () => {
    expect(make().canSubmit).toBe(false);
  });

  it('false quand formulaire valide mais pas de CSV', () => {
    const comp = make();
    setForm(comp, 'Acme SAS', 'acme.fr');
    expect(comp.canSubmit).toBe(false);
  });

  it('false quand CSV présent mais formulaire invalide', () => {
    const comp = make();
    (comp as any).csvFile.set(makeFile());
    expect(comp.canSubmit).toBe(false);
  });

  it('true quand formulaire valide + CSV présent', () => {
    const comp = make();
    setForm(comp, 'Acme SAS', 'acme.fr');
    (comp as any).csvFile.set(makeFile());
    expect(comp.canSubmit).toBe(true);
  });

  it('false quand submitting est true', () => {
    const comp = make();
    setForm(comp, 'Acme SAS', 'acme.fr');
    (comp as any).csvFile.set(makeFile());
    (comp as any).submitting.set(true);
    expect(comp.canSubmit).toBe(false);
  });
});

// ── company_name validation ───────────────────────────────────────────────────

describe('DarkwebDossierNewComponent — company_name validation', () => {
  it('invalide quand vide', () => {
    const comp = make();
    comp.form.get('company_name')!.setValue('');
    expect(comp.form.get('company_name')!.valid).toBe(false);
  });

  it('invalide quand un seul caractère (minLength 2)', () => {
    const comp = make();
    comp.form.get('company_name')!.setValue('A');
    expect(comp.form.get('company_name')!.valid).toBe(false);
  });

  it('valide pour deux caractères minimum', () => {
    const comp = make();
    comp.form.get('company_name')!.setValue('AB');
    expect(comp.form.get('company_name')!.valid).toBe(true);
  });

  it('valide pour un nom standard', () => {
    const comp = make();
    comp.form.get('company_name')!.setValue('Acme SAS');
    expect(comp.form.get('company_name')!.valid).toBe(true);
  });

  it('invalide quand dépasse 200 caractères', () => {
    const comp = make();
    comp.form.get('company_name')!.setValue('A'.repeat(201));
    expect(comp.form.get('company_name')!.valid).toBe(false);
  });

  it('valide pour exactement 200 caractères', () => {
    const comp = make();
    comp.form.get('company_name')!.setValue('A'.repeat(200));
    expect(comp.form.get('company_name')!.valid).toBe(true);
  });
});

// ── domain validation ─────────────────────────────────────────────────────────

describe('DarkwebDossierNewComponent — domain validation', () => {
  it('invalide quand vide', () => {
    const comp = make();
    comp.form.get('domain')!.setValue('');
    expect(comp.form.get('domain')!.valid).toBe(false);
  });

  it('valide pour acme.fr', () => {
    const comp = make();
    comp.form.get('domain')!.setValue('acme.fr');
    expect(comp.form.get('domain')!.valid).toBe(true);
  });

  it('valide pour sous-domaine sub.acme.com', () => {
    const comp = make();
    comp.form.get('domain')!.setValue('sub.acme.com');
    expect(comp.form.get('domain')!.valid).toBe(true);
  });

  it('invalide pour un domaine sans extension (acme)', () => {
    const comp = make();
    comp.form.get('domain')!.setValue('acme');
    expect(comp.form.get('domain')!.valid).toBe(false);
  });

  it('invalide pour une URL complète avec https://', () => {
    const comp = make();
    comp.form.get('domain')!.setValue('https://acme.fr');
    expect(comp.form.get('domain')!.valid).toBe(false);
  });

  it('invalide pour un domaine avec espace', () => {
    const comp = make();
    comp.form.get('domain')!.setValue('ac me.fr');
    expect(comp.form.get('domain')!.valid).toBe(false);
  });

  it('valide pour domaine avec tiret (my-company.io)', () => {
    const comp = make();
    comp.form.get('domain')!.setValue('my-company.io');
    expect(comp.form.get('domain')!.valid).toBe(true);
  });

  it("invalide pour TLD d'un seul caractère", () => {
    const comp = make();
    comp.form.get('domain')!.setValue('acme.f');
    expect(comp.form.get('domain')!.valid).toBe(false);
  });
});

// ── onFileChange ──────────────────────────────────────────────────────────────

describe('DarkwebDossierNewComponent — onFileChange()', () => {
  it('rejette un fichier non-.csv', () => {
    const comp = make();
    const file = new File(['data'], 'doc.pdf', { type: 'application/pdf' });
    const event = { target: { files: [file] } } as unknown as Event;
    comp.onFileChange(event);
    expect((comp as any).csvFile()).toBeNull();
    expect((comp as any).csvError()).toContain('Format invalide');
  });

  it('rejette un fichier trop lourd (> 2 Mo)', () => {
    const comp = make();
    const bigContent = 'x'.repeat(2 * 1024 * 1024 + 1);
    const file = new File([bigContent], 'big.csv', { type: 'text/csv' });
    const event = { target: { files: [file] } } as unknown as Event;
    comp.onFileChange(event);
    expect((comp as any).csvFile()).toBeNull();
    expect((comp as any).csvError()).toContain('trop lourd');
  });

  it('réinitialise les erreurs si pas de fichier sélectionné', () => {
    const comp = make();
    (comp as any).csvError.set('old error');
    const event = { target: { files: [] } } as unknown as Event;
    comp.onFileChange(event);
    expect((comp as any).csvError()).toBeNull();
    expect((comp as any).csvFile()).toBeNull();
  });
});

// ── submit guard ──────────────────────────────────────────────────────────────

describe('DarkwebDossierNewComponent — submit()', () => {
  it("n'appelle pas service.create si canSubmit est false", () => {
    const comp = make();
    comp.submit();
    expect((comp as any).service.create).not.toHaveBeenCalled();
  });
});
