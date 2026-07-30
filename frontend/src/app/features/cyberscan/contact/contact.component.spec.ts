/**
 * ContactComponent — tests via injection de dépendances (HttpClient/Title/Meta mockés).
 */
import { describe, it, expect, vi } from 'vitest';
import { Injector, runInInjectionContext } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { Title, Meta } from '@angular/platform-browser';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { of, throwError } from 'rxjs';

async function makeComponent() {
  const { ContactComponent } = await import('./contact.component');
  const httpMock = { post: vi.fn() };
  const injector = Injector.create({
    providers: [
      { provide: FormBuilder, useValue: new FormBuilder() },
      { provide: HttpClient, useValue: httpMock },
      { provide: Title, useValue: { setTitle: vi.fn() } },
      { provide: Meta, useValue: { updateTag: vi.fn() } },
      // Le composant lit ?subject= pour pre-selectionner le type de besoin.
      {
        provide: ActivatedRoute,
        useValue: { snapshot: { queryParamMap: { get: () => null } } },
      },
    ],
  });
  const comp = runInInjectionContext(injector, () => new ContactComponent());
  return { comp, httpMock };
}

const VALID = {
  name: 'Alice Martin',
  email: 'alice@example.com',
  phone: '',
  need_type: 'audit-flash',
  site_url: '',
  message: 'Bonjour, je souhaite un audit de mon site.',
  rgpd: true,
};

describe('ContactComponent — état initial', () => {
  it('status est idle au départ', async () => {
    const { comp } = await makeComponent();
    expect(comp.status).toBe('idle');
  });

  it('expose les options de besoin', async () => {
    const { comp } = await makeComponent();
    expect(comp.needOptions.length).toBeGreaterThan(0);
  });
});

describe('ContactComponent — validation', () => {
  it('invalide si vide', async () => {
    const { comp } = await makeComponent();
    expect(comp.form.invalid).toBe(true);
  });

  it('invalide si rgpd non coché', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ ...VALID, rgpd: false });
    expect(comp.form.invalid).toBe(true);
  });

  it('invalide si message trop court', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue({ ...VALID, message: 'court' });
    expect(comp.form.invalid).toBe(true);
  });

  it('valide avec un formulaire complet', async () => {
    const { comp } = await makeComponent();
    comp.form.setValue(VALID);
    expect(comp.form.valid).toBe(true);
  });
});

describe('ContactComponent — submit()', () => {
  it("ne fait pas d'appel HTTP si invalide", async () => {
    const { comp, httpMock } = await makeComponent();
    comp.submit();
    expect(httpMock.post).not.toHaveBeenCalled();
  });

  it('envoie le payload SANS le champ rgpd', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(of({ message: 'ok' }));
    comp.form.setValue(VALID);
    comp.submit();
    const [, payload] = httpMock.post.mock.calls[0];
    expect(payload).not.toHaveProperty('rgpd');
    expect(payload).toMatchObject({ name: 'Alice Martin', email: 'alice@example.com' });
  });

  it('status passe à sent après succès', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(of({ message: 'ok' }));
    comp.form.setValue(VALID);
    comp.submit();
    expect(comp.status).toBe('sent');
  });

  it('status passe à error + message après échec', async () => {
    const { comp, httpMock } = await makeComponent();
    httpMock.post.mockReturnValue(throwError(() => ({ error: { detail: 'Boom' } })));
    comp.form.setValue(VALID);
    comp.submit();
    expect(comp.status).toBe('error');
    expect(comp.errorMessage).toBe('Boom');
  });
});

// ── Pré-sélection depuis ?subject= ────────────────────────────────────────────
//
// Le paramètre était passé par les liens des pages tarifs mais n'était lu nulle
// part : une demande partenaire arrivait indistinguable d'un contact ordinaire.

async function makeComponentAvecSujet(sujet: string | null) {
  const { ContactComponent } = await import('./contact.component');
  const injector = Injector.create({
    providers: [
      { provide: FormBuilder, useValue: new FormBuilder() },
      { provide: HttpClient, useValue: { post: vi.fn() } },
      { provide: Title, useValue: { setTitle: vi.fn() } },
      { provide: Meta, useValue: { updateTag: vi.fn() } },
      {
        provide: ActivatedRoute,
        useValue: { snapshot: { queryParamMap: { get: () => sujet } } },
      },
    ],
  });
  return runInInjectionContext(injector, () => new ContactComponent());
}

describe('ContactComponent — pré-sélection via ?subject=', () => {
  it('pré-sélectionne une demande partenaire', async () => {
    const comp = await makeComponentAvecSujet('partenaire-sensibilisation');
    comp.ngOnInit();
    expect(comp.form.value.need_type).toBe('partenaire-sensibilisation');
  });

  it('pré-sélectionne la sensibilisation', async () => {
    const comp = await makeComponentAvecSujet('sensibilisation-nis2');
    comp.ngOnInit();
    expect(comp.form.value.need_type).toBe('sensibilisation-nis2');
  });

  it('ignore une valeur inconnue plutôt que de casser le formulaire', async () => {
    const comp = await makeComponentAvecSujet('valeur-bidon');
    comp.ngOnInit();
    expect(comp.form.value.need_type).toBe('');
  });

  it('sans paramètre, le champ reste vide', async () => {
    const comp = await makeComponentAvecSujet(null);
    comp.ngOnInit();
    expect(comp.form.value.need_type).toBe('');
  });
});
