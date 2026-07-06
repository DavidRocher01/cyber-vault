import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { signal } from '@angular/core';
import { FormBuilder, FormArray, Validators } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { PcaComponent } from './pca.component';

function make(overrides: { pca?: any } = {}): PcaComponent {
  const comp = Object.create(PcaComponent.prototype) as PcaComponent;
  const fb = new FormBuilder();
  (comp as any).fb = fb;
  (comp as any).generating = signal(false);
  (comp as any).snack = { open: vi.fn() };
  (comp as any).title = { setTitle: vi.fn() };
  (comp as any).pca = {
    generate: vi.fn(() => of(new Blob(['pdf'], { type: 'application/pdf' }))),
    ...overrides.pca,
  };

  (comp as any).companyForm = fb.nonNullable.group({
    name: ['', Validators.required],
    sector: [''],
    contact: [''],
    email: [''],
    phone: [''],
  });
  (comp as any).systemsForm = fb.group({
    systems: fb.array([(comp as any)._newSystem()]),
  });
  (comp as any).teamForm = fb.group({
    members: fb.array([(comp as any)._newMember()]),
  });
  (comp as any).commForm = fb.nonNullable.group({
    communication_plan: [''],
  });
  return comp;
}

// ── FormArray getters + _newSystem / _newMember ─────────────────────────────────

describe('PcaComponent — getters systems / members', () => {
  it('systems retourne un FormArray avec un système initial', () => {
    const comp = make();
    expect(comp.systems).toBeInstanceOf(FormArray);
    expect(comp.systems.length).toBe(1);
  });

  it('members retourne un FormArray avec un membre initial', () => {
    const comp = make();
    expect(comp.members).toBeInstanceOf(FormArray);
    expect(comp.members.length).toBe(1);
  });

  it('un système a des valeurs par défaut rto=4 / rpo=1', () => {
    const comp = make();
    const sys = comp.systems.at(0).getRawValue();
    expect(sys.rto_hours).toBe(4);
    expect(sys.rpo_hours).toBe(1);
  });

  it('le nom d’un système est requis', () => {
    const comp = make();
    expect(comp.systems.at(0).get('name')!.valid).toBe(false);
  });

  it('rto_hours doit être >= 1', () => {
    const comp = make();
    const ctrl = comp.systems.at(0).get('rto_hours')!;
    ctrl.setValue(0);
    expect(ctrl.valid).toBe(false);
    ctrl.setValue(1);
    expect(ctrl.valid).toBe(true);
  });

  it('le nom d’un membre est requis', () => {
    const comp = make();
    expect(comp.members.at(0).get('name')!.valid).toBe(false);
  });
});

// ── addSystem / removeSystem ────────────────────────────────────────────────────

describe('PcaComponent — addSystem() / removeSystem()', () => {
  it('addSystem ajoute un système', () => {
    const comp = make();
    comp.addSystem();
    expect(comp.systems.length).toBe(2);
  });

  it('removeSystem retire le système à l’index donné', () => {
    const comp = make();
    comp.addSystem();
    comp.systems.at(1).get('name')!.setValue('Second');
    comp.removeSystem(0);
    expect(comp.systems.length).toBe(1);
    expect(comp.systems.at(0).get('name')!.value).toBe('Second');
  });

  it('removeSystem ne retire jamais le dernier système', () => {
    const comp = make();
    comp.removeSystem(0);
    expect(comp.systems.length).toBe(1);
  });
});

// ── addMember / removeMember ────────────────────────────────────────────────────

describe('PcaComponent — addMember() / removeMember()', () => {
  it('addMember ajoute un membre', () => {
    const comp = make();
    comp.addMember();
    expect(comp.members.length).toBe(2);
  });

  it('removeMember retire le membre à l’index donné', () => {
    const comp = make();
    comp.addMember();
    comp.members.at(1).get('name')!.setValue('Bob');
    comp.removeMember(0);
    expect(comp.members.length).toBe(1);
    expect(comp.members.at(0).get('name')!.value).toBe('Bob');
  });

  it('removeMember ne retire jamais le dernier membre', () => {
    const comp = make();
    comp.removeMember(0);
    expect(comp.members.length).toBe(1);
  });
});

// ── generate : garde formulaire invalide ────────────────────────────────────────

describe('PcaComponent — generate() garde', () => {
  it('n’appelle pas pca.generate si companyForm est invalide (name manquant)', () => {
    const comp = make();
    comp.generate();
    expect((comp as any).pca.generate).not.toHaveBeenCalled();
  });

  it('ne passe pas generating à true si le formulaire est invalide', () => {
    const comp = make();
    comp.generate();
    expect((comp as any).generating()).toBe(false);
  });
});

// ── generate : construction du payload + succès ─────────────────────────────────

describe('PcaComponent — generate() succès', () => {
  let createSpy: any;
  let revokeSpy: any;
  let clickSpy: any;

  beforeEach(() => {
    createSpy = vi.fn(() => 'blob:mock');
    revokeSpy = vi.fn();
    (URL as any).createObjectURL = createSpy;
    (URL as any).revokeObjectURL = revokeSpy;
    clickSpy = vi.fn();
    vi.spyOn(document, 'createElement').mockImplementation(((tag: string) => {
      if (tag === 'a') return { href: '', download: '', click: clickSpy } as any;
      return {} as any;
    }) as any);
  });

  afterEach(() => vi.restoreAllMocks());

  function fill(comp: PcaComponent) {
    comp.companyForm.setValue({
      name: 'Acme SAS',
      sector: 'IT',
      contact: 'Jean',
      email: 'j@acme.fr',
      phone: '06',
    });
  }

  it('appelle pca.generate quand companyForm est valide', () => {
    const comp = make();
    fill(comp);
    comp.generate();
    expect((comp as any).pca.generate).toHaveBeenCalledTimes(1);
  });

  it('exclut les systèmes sans nom du payload', () => {
    const comp = make();
    fill(comp);
    comp.systems.at(0).get('name')!.setValue('  '); // blanc -> filtré
    comp.addSystem();
    comp.systems.at(1).get('name')!.setValue('ERP');
    comp.generate();
    const payload = (comp as any).pca.generate.mock.calls[0][0];
    expect(payload.critical_systems).toHaveLength(1);
    expect(payload.critical_systems[0].name).toBe('ERP');
  });

  it('exclut les membres sans nom du payload', () => {
    const comp = make();
    fill(comp);
    comp.members.at(0).get('name')!.setValue('');
    comp.addMember();
    comp.members.at(1).get('name')!.setValue('Alice');
    comp.generate();
    const payload = (comp as any).pca.generate.mock.calls[0][0];
    expect(payload.response_team).toHaveLength(1);
    expect(payload.response_team[0].name).toBe('Alice');
  });

  it('inclut le plan de communication dans le payload', () => {
    const comp = make();
    fill(comp);
    comp.commForm.setValue({ communication_plan: 'Appeler le CERT' });
    comp.generate();
    const payload = (comp as any).pca.generate.mock.calls[0][0];
    expect(payload.communication_plan).toBe('Appeler le CERT');
  });

  it('déclenche le téléchargement du blob (createObjectURL + click + revoke)', () => {
    const comp = make();
    fill(comp);
    comp.generate();
    expect(createSpy).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeSpy).toHaveBeenCalledTimes(1);
  });

  it('nomme le fichier avec le nom de société normalisé', () => {
    const comp = make();
    fill(comp);
    let anchor: any;
    (document.createElement as any).mockImplementation((tag: string) => {
      anchor = { href: '', download: '', click: clickSpy };
      return anchor;
    });
    comp.generate();
    expect(anchor.download).toBe('pca_acme_sas.pdf');
  });

  it('repasse generating à false après succès', () => {
    const comp = make();
    fill(comp);
    comp.generate();
    expect((comp as any).generating()).toBe(false);
  });

  it('affiche un message de succès', () => {
    const comp = make();
    fill(comp);
    comp.generate();
    expect((comp as any).snack.open).toHaveBeenCalledWith(
      'PCA téléchargé',
      'OK',
      expect.anything()
    );
  });
});

// ── generate : gestion d’erreur ─────────────────────────────────────────────────

describe('PcaComponent — generate() erreur', () => {
  it('repasse generating à false et affiche une erreur', () => {
    const comp = make({
      pca: { generate: vi.fn(() => throwError(() => new Error('500'))) },
    });
    comp.companyForm.get('name')!.setValue('Acme');
    comp.generate();
    expect((comp as any).generating()).toBe(false);
    expect((comp as any).snack.open).toHaveBeenCalledWith(
      'Erreur lors de la génération',
      'Fermer',
      expect.anything()
    );
  });
});
