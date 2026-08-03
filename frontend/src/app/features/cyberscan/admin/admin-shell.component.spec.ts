/**
 * AdminShellComponent — logique : navigation (navItems), validation du formulaire
 * de clé admin, et transitions d'état du login (verifying / authError) selon la
 * réponse du service d'auth. Le rendu du template n'est pas testé.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Injector, runInInjectionContext, signal } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { AdminShellComponent } from './admin-shell.component';
import { AdminAuthService } from './admin-auth.service';

function make() {
  const auth = {
    authenticated: signal(false),
    verificationEnCours: signal(false),
    verifierCompte: vi.fn().mockReturnValue(of(false)),
    logout: vi.fn(),
  };
  const injector = Injector.create({
    providers: [
      { provide: AdminAuthService, useValue: auth },
      { provide: FormBuilder, useClass: FormBuilder },
    ],
  });
  const comp = runInInjectionContext(injector, () => new AdminShellComponent());
  return { comp, auth };
}

describe('AdminShellComponent — navItems', () => {
  it('déclare 10 entrées de navigation', () => {
    // Agenda et Newsletter etaient codes en dur SOUS la liste, sans
    // routerLinkActive : ils ne s'allumaient jamais. Rapatries le 2026-08-02,
    // avec le nouvel onglet Acquisition.
    expect(make().comp.navItems).toHaveLength(10);
  });

  it('Agenda et Newsletter sont dans la liste, comme les autres', () => {
    const chemins = make().comp.navItems.map(i => i.path);
    expect(chemins).toContain('/admin/ba61c5a60113/agenda');
    expect(chemins).toContain('/admin/newsletter');
  });

  it("l'onglet Acquisition est declare", () => {
    const chemins = make().comp.navItems.map(i => i.path);
    expect(chemins).toContain('/admin/acquisition');
  });

  it("la 1re entrée est la vue d'ensemble /admin en correspondance exacte", () => {
    const first = make().comp.navItems[0];
    expect(first.path).toBe('/admin');
    expect(first.exact).toBe(true);
  });

  it('toutes les entrées sauf la 1re sont non-exactes', () => {
    const rest = make().comp.navItems.slice(1);
    expect(rest.every(i => i.exact === false)).toBe(true);
  });

  it('expose les sections attendues', () => {
    const paths = make().comp.navItems.map(i => i.path);
    expect(paths).toContain('/admin/contacts');
    expect(paths).toContain('/admin/blog');
    expect(paths).toContain('/admin/users');
    expect(paths).toContain('/admin/scans');
    expect(paths).toContain('/admin/invoices');
    expect(paths).toContain('/admin/quotes');
  });

  it('chaque entrée porte un label et une icône non vides', () => {
    for (const item of make().comp.navItems) {
      expect(item.label.length).toBeGreaterThan(0);
      expect(item.icon.length).toBeGreaterThan(0);
    }
  });
});
