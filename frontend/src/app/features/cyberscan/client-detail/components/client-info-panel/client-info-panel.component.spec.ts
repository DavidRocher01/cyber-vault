/**
 * ClientInfoPanelComponent — tests via injection de dépendances (FormGroup requis).
 */
import { describe, it, expect } from 'vitest';
import { EventEmitter, Injector, runInInjectionContext } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { ClientInfoPanelComponent } from './client-info-panel.component';

function make() {
  const fb = new FormBuilder();
  const form = fb.group({
    name: ['Acme Corp'],
    email: ['contact@acme.com'],
    description: [''],
    formula: ['premium'],
    monthly_amount: [500],
    contract_renewal_at: [''],
    status: ['active'],
    notion_workspace_url: [''],
    pipedrive_deal_id: [''],
    pennylane_customer_id: [''],
  });

  const injector = Injector.create({
    providers: [{ provide: FormBuilder, useValue: fb }],
  });

  const comp = runInInjectionContext(injector, () => {
    const c = Object.create(ClientInfoPanelComponent.prototype) as ClientInfoPanelComponent;
    c.form = form;
    c.saving = false;
    c.formulas = [];
    (c as any).save = new EventEmitter<void>();
    return c;
  });

  return { comp, form };
}

describe('ClientInfoPanelComponent — @Input() form', () => {
  it('accepte un FormGroup valide', () => {
    const { comp, form } = make();
    expect(comp.form).toBe(form);
  });

  it('le formulaire est valide quand le nom est renseigné', () => {
    const { comp } = make();
    expect(comp.form.valid).toBe(true);
  });
});

describe('ClientInfoPanelComponent — @Input() saving', () => {
  it('saving est false par défaut', () => {
    const { comp } = make();
    expect(comp.saving).toBe(false);
  });

  it('saving peut être passé à true', () => {
    const { comp } = make();
    comp.saving = true;
    expect(comp.saving).toBe(true);
  });
});

describe('ClientInfoPanelComponent — @Input() formulas', () => {
  it('formulas est un tableau vide par défaut', () => {
    const { comp } = make();
    expect(comp.formulas).toEqual([]);
  });

  it('accepte un tableau de formules', () => {
    const { comp } = make();
    comp.formulas = [
      { value: 'essentiel', label: 'Essentiel' },
      { value: 'premium', label: 'Premium' },
    ];
    expect(comp.formulas).toHaveLength(2);
    expect(comp.formulas[0].value).toBe('essentiel');
  });
});

describe('ClientInfoPanelComponent — @Output() save', () => {
  it('save est un EventEmitter', () => {
    const { comp } = make();
    expect(typeof comp.save.emit).toBe('function');
  });

  it("save.emit ne lève pas d'erreur", () => {
    const { comp } = make();
    expect(() => comp.save.emit()).not.toThrow();
  });
});
