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
    verify: vi.fn(),
    login: vi.fn(),
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
  it('déclare 7 entrées de navigation', () => {
    expect(make().comp.navItems).toHaveLength(7);
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

describe('AdminShellComponent — validation du formulaire', () => {
  it('le formulaire est invalide sans clé', () => {
    expect(make().comp.keyForm.invalid).toBe(true);
  });

  it("le formulaire devient valide dès qu'une clé est saisie", () => {
    const { comp } = make();
    comp.keyForm.setValue({ key: 'secret' });
    expect(comp.keyForm.valid).toBe(true);
  });

  it('démarre avec verifying=false et authError vide', () => {
    const { comp } = make();
    expect(comp.verifying()).toBe(false);
    expect(comp.authError()).toBe('');
  });
});

describe('AdminShellComponent — login()', () => {
  let ctx: ReturnType<typeof make>;
  beforeEach(() => {
    ctx = make();
    ctx.comp.keyForm.setValue({ key: 'my-key' });
  });

  it('appelle verify() avec la clé saisie', () => {
    ctx.auth.verify.mockReturnValue(of({}));
    ctx.comp.login();
    expect(ctx.auth.verify).toHaveBeenCalledWith('my-key');
  });

  it("succès -> login(clé) appelé, verifying repasse à false, pas d'erreur", () => {
    ctx.auth.verify.mockReturnValue(of({}));
    ctx.comp.login();
    expect(ctx.auth.login).toHaveBeenCalledWith('my-key');
    expect(ctx.comp.verifying()).toBe(false);
    expect(ctx.comp.authError()).toBe('');
  });

  it("échec -> message d'erreur affiché, verifying=false, login() non appelé", () => {
    ctx.auth.verify.mockReturnValue(throwError(() => new Error('401')));
    ctx.comp.login();
    expect(ctx.comp.authError()).toBe('Clé admin incorrecte.');
    expect(ctx.comp.verifying()).toBe(false);
    expect(ctx.auth.login).not.toHaveBeenCalled();
  });

  it('efface une erreur précédente avant une tentative réussie', () => {
    ctx.comp.authError.set('ancienne erreur');
    ctx.auth.verify.mockReturnValue(of({}));
    ctx.comp.login();
    expect(ctx.comp.authError()).toBe('');
  });

  it('clé absente -> verify() appelé avec chaîne vide', () => {
    const { comp, auth } = make();
    auth.verify.mockReturnValue(of({}));
    comp.login();
    expect(auth.verify).toHaveBeenCalledWith('');
  });
});
