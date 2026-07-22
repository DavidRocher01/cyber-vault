import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ClientDetailComponent } from './client-detail.component';

function make(): ClientDetailComponent {
  return Object.create(ClientDetailComponent.prototype) as ClientDetailComponent;
}

// ── docTypeLabel ──────────────────────────────────────────────────────────────

describe('ClientDetailComponent — docTypeLabel()', () => {
  it('retourne "Compte-rendu" pour compte_rendu', () =>
    expect(make().docTypeLabel('compte_rendu')).toBe('Compte-rendu'));
  it('retourne "Rapport" pour rapport', () =>
    expect(make().docTypeLabel('rapport')).toBe('Rapport'));
  it('retourne "Recommandation" pour recommandation', () =>
    expect(make().docTypeLabel('recommandation')).toBe('Recommandation'));
  it('retourne "Contrat" pour contrat', () =>
    expect(make().docTypeLabel('contrat')).toBe('Contrat'));
  it('retourne "Autre" pour autre', () => expect(make().docTypeLabel('autre')).toBe('Autre'));
  it('retourne la valeur brute pour type inconnu', () =>
    expect(make().docTypeLabel('custom')).toBe('custom'));
});

// ── docTypeClass ──────────────────────────────────────────────────────────────

describe('ClientDetailComponent — docTypeClass()', () => {
  it('contient blue pour compte_rendu', () =>
    expect(make().docTypeClass('compte_rendu')).toContain('blue'));
  it('contient cyan pour rapport', () => expect(make().docTypeClass('rapport')).toContain('cyan'));
  it('contient purple pour recommandation', () =>
    expect(make().docTypeClass('recommandation')).toContain('purple'));
  it('retourne classe gray pour type inconnu', () =>
    expect(make().docTypeClass('autre')).toContain('gray'));
});

// ── statusClass ───────────────────────────────────────────────────────────────

describe('ClientDetailComponent — statusClass()', () => {
  it('contient green pour active', () => expect(make().statusClass('active')).toContain('green'));
  it('contient yellow pour inactive', () =>
    expect(make().statusClass('inactive')).toContain('yellow'));
  it('contient red pour churned', () => expect(make().statusClass('churned')).toContain('red'));
  it('retourne gray pour inconnu', () => expect(make().statusClass('other')).toContain('gray'));
});

// ── priorityClass ─────────────────────────────────────────────────────────────

describe('ClientDetailComponent — priorityClass()', () => {
  it('contient red pour critical', () => expect(make().priorityClass('critical')).toContain('red'));
  it('contient orange pour high', () => expect(make().priorityClass('high')).toContain('orange'));
  it('contient yellow pour medium', () =>
    expect(make().priorityClass('medium')).toContain('yellow'));
  it('contient green/blue/gray pour low', () => {
    const cls = make().priorityClass('low');
    expect(cls).toBeDefined();
    expect(cls.length).toBeGreaterThan(0);
  });
});

// ── actionStatusLabel ─────────────────────────────────────────────────────────

describe('ClientDetailComponent — actionStatusLabel()', () => {
  it('retourne "Ouverte" pour open', () =>
    expect(make().actionStatusLabel('open')).toBe('Ouverte'));
  it('retourne "En cours" pour in_progress', () =>
    expect(make().actionStatusLabel('in_progress')).toBe('En cours'));
  it('retourne "Terminée" pour done', () =>
    expect(make().actionStatusLabel('done')).toBe('Terminée'));
  it('retourne "Annulée" pour cancelled', () =>
    expect(make().actionStatusLabel('cancelled')).toBe('Annulée'));
  it('retourne "Reportée" pour postponed', () =>
    expect(make().actionStatusLabel('postponed')).toBe('Reportée'));
  it('retourne la valeur brute pour inconnu', () =>
    expect(make().actionStatusLabel('other')).toBe('other'));
});

// ── visitStatusLabel ──────────────────────────────────────────────────────────

describe('ClientDetailComponent — visitStatusLabel()', () => {
  it('retourne "Planifiée" pour planned', () =>
    expect(make().visitStatusLabel('planned')).toBe('Planifiée'));
  it('retourne "Complétée" pour completed', () =>
    expect(make().visitStatusLabel('completed')).toBe('Complétée'));
  it('retourne "Annulée" pour cancelled', () =>
    expect(make().visitStatusLabel('cancelled')).toBe('Annulée'));
  it('retourne "Reportée" pour postponed', () =>
    expect(make().visitStatusLabel('postponed')).toBe('Reportée'));
  it('retourne valeur brute pour inconnu', () =>
    expect(make().visitStatusLabel('other')).toBe('other'));
});

// ── visitTypeLabel ────────────────────────────────────────────────────────────

describe('ClientDetailComponent — visitTypeLabel()', () => {
  it('retourne "Mensuelle" pour monthly', () =>
    expect(make().visitTypeLabel('monthly')).toBe('Mensuelle'));
  it('retourne "Trimestrielle" pour quarterly', () =>
    expect(make().visitTypeLabel('quarterly')).toBe('Trimestrielle'));
  it('retourne "Annuelle" pour annual', () =>
    expect(make().visitTypeLabel('annual')).toBe('Annuelle'));
  it('retourne "Urgente" pour urgent', () =>
    expect(make().visitTypeLabel('urgent')).toBe('Urgente'));
  it('retourne valeur brute pour inconnu', () =>
    expect(make().visitTypeLabel('other')).toBe('other'));
});

// ── locationLabel ─────────────────────────────────────────────────────────────

describe('ClientDetailComponent — locationLabel()', () => {
  it('retourne "Sur site" pour onsite', () =>
    expect(make().locationLabel('onsite')).toBe('Sur site'));
  it('retourne "À distance" pour remote', () =>
    expect(make().locationLabel('remote')).toBe('À distance'));
  it('retourne "À distance" pour valeur inconnue', () =>
    expect(make().locationLabel('other')).toBe('À distance'));
});

// ── activityLabel ─────────────────────────────────────────────────────────────

describe('ClientDetailComponent — activityLabel()', () => {
  it('retourne le bon libellé pour view_client', () =>
    expect(make().activityLabel('view_client')).toBe('Consultation fiche client'));
  it('retourne le bon libellé pour generate_report', () =>
    expect(make().activityLabel('generate_report')).toBe('Génération de rapport'));
  it('retourne le bon libellé pour create_action', () =>
    expect(make().activityLabel('create_action')).toBe("Création d'une action"));
  it('retourne la valeur brute pour inconnu', () =>
    expect(make().activityLabel('custom_action')).toBe('custom_action'));
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('ClientDetailComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("retourne une date formatée contenant l'année", () => {
    const result = make().formatDate('2024-06-15');
    expect(result).toContain('2024');
  });
});

// ── formatAmount ──────────────────────────────────────────────────────────────

describe('ClientDetailComponent — formatAmount()', () => {
  it('retourne "—" pour null', () => expect(make().formatAmount(null)).toBe('—'));
  it('contient € pour un montant valide', () => expect(make().formatAmount(2000)).toContain('€'));
});

// ── visitStatusClass ──────────────────────────────────────────────────────────

describe('ClientDetailComponent — visitStatusClass()', () => {
  it('contient green pour completed', () =>
    expect(make().visitStatusClass('completed')).toContain('green'));
  it('contient red pour cancelled', () =>
    expect(make().visitStatusClass('cancelled')).toContain('red'));
  it('contient yellow pour postponed', () =>
    expect(make().visitStatusClass('postponed')).toContain('yellow'));
  it('contient blue pour planned', () =>
    expect(make().visitStatusClass('planned')).toContain('blue'));
});

// ── formulaLabel ──────────────────────────────────────────────────────────────

describe('ClientDetailComponent — formulaLabel()', () => {
  it('retourne "Essentiel" pour essentiel', () =>
    expect(make().formulaLabel('essentiel')).toBe('Essentiel'));
  it('retourne "Premium" pour premium', () =>
    expect(make().formulaLabel('premium')).toBe('Premium'));
  it('retourne "Excellence" pour excellence', () =>
    expect(make().formulaLabel('excellence')).toBe('Excellence'));
  it('retourne "—" pour null', () => expect(make().formulaLabel(null)).toBe('—'));
  it('retourne la valeur brute pour inconnu', () =>
    expect(make().formulaLabel('custom')).toBe('custom'));
});

// ── formulaClass ──────────────────────────────────────────────────────────────

describe('ClientDetailComponent — formulaClass()', () => {
  it('contient blue pour essentiel', () =>
    expect(make().formulaClass('essentiel')).toContain('blue'));
  it('contient purple pour premium', () =>
    expect(make().formulaClass('premium')).toContain('purple'));
  it('contient amber pour excellence', () =>
    expect(make().formulaClass('excellence')).toContain('amber'));
  it('contient gray pour null', () => expect(make().formulaClass(null)).toContain('gray'));
  it('contient gray pour inconnu', () => expect(make().formulaClass('custom')).toContain('gray'));
});

// ── actionStatusClass ─────────────────────────────────────────────────────────

describe('ClientDetailComponent — actionStatusClass()', () => {
  it('contient green pour done', () => expect(make().actionStatusClass('done')).toContain('green'));
  it('contient blue pour in_progress', () =>
    expect(make().actionStatusClass('in_progress')).toContain('blue'));
  it('contient gray pour cancelled', () =>
    expect(make().actionStatusClass('cancelled')).toContain('gray'));
  it('contient yellow pour postponed', () =>
    expect(make().actionStatusClass('postponed')).toContain('yellow'));
  it('retourne classe par défaut pour open', () => {
    const cls = make().actionStatusClass('open');
    expect(cls).toContain('white');
  });
});

// ── scanStatusClass ───────────────────────────────────────────────────────────

describe('ClientDetailComponent — scanStatusClass()', () => {
  it('contient green pour OK', () => expect(make().scanStatusClass('OK')).toContain('green'));
  it('contient yellow pour WARNING', () =>
    expect(make().scanStatusClass('WARNING')).toContain('yellow'));
  it('contient red pour CRITICAL', () =>
    expect(make().scanStatusClass('CRITICAL')).toContain('red'));
  it('contient gray pour null', () => expect(make().scanStatusClass(null)).toContain('gray'));
});

// ── scanStatusLabel ───────────────────────────────────────────────────────────

describe('ClientDetailComponent — scanStatusLabel()', () => {
  it('retourne "Aucun scan" pour null', () =>
    expect(make().scanStatusLabel(null)).toBe('Aucun scan'));
  it('retourne le statut brut pour OK', () => expect(make().scanStatusLabel('OK')).toBe('OK'));
  it('retourne le statut brut pour WARNING', () =>
    expect(make().scanStatusLabel('WARNING')).toBe('WARNING'));
  it('retourne le statut brut pour CRITICAL', () =>
    expect(make().scanStatusLabel('CRITICAL')).toBe('CRITICAL'));
});

// ── formatDateTime ────────────────────────────────────────────────────────────

describe('ClientDetailComponent — formatDateTime()', () => {
  it("inclut l'année", () =>
    expect(make().formatDateTime('2024-03-15T10:30:00Z')).toContain('2024'));
  it("inclut l'heure", () =>
    expect(make().formatDateTime('2024-03-15T10:30:00Z')).toMatch(/\d{2}:\d{2}/));
});

// ── openActionsCount / overdueActionsCount ─────────────────────────────────────

describe('ClientDetailComponent — openActionsCount', () => {
  it('compte les actions open et in_progress', () => {
    const c = make();
    (c as any).actions = signal([
      { status: 'open' },
      { status: 'in_progress' },
      { status: 'done' },
      { status: 'cancelled' },
    ]);
    expect(c.openActionsCount).toBe(2);
  });

  it('retourne 0 sur liste vide', () => {
    const c = make();
    (c as any).actions = signal([]);
    expect(c.openActionsCount).toBe(0);
  });
});

describe('ClientDetailComponent — overdueActionsCount', () => {
  it('compte les actions ouvertes échues', () => {
    const c = make();
    (c as any).actions = signal([
      { status: 'open', due_date: '2000-01-01' },
      { status: 'in_progress', due_date: '2000-01-01' },
      { status: 'open', due_date: '2999-01-01' },
      { status: 'done', due_date: '2000-01-01' },
      { status: 'open', due_date: null },
    ]);
    expect(c.overdueActionsCount).toBe(2);
  });

  it('retourne 0 quand aucune action échue', () => {
    const c = make();
    (c as any).actions = signal([{ status: 'open', due_date: '2999-01-01' }]);
    expect(c.overdueActionsCount).toBe(0);
  });
});

// ── confirmDeleteLabel ────────────────────────────────────────────────────────

describe('ClientDetailComponent — confirmDeleteLabel()', () => {
  function makeWith(cd: unknown): ClientDetailComponent {
    const c = make();
    (c as any).confirmDelete = signal(cd);
    return c;
  }

  it('retourne "" quand rien à supprimer', () =>
    expect(makeWith(null).confirmDeleteLabel()).toBe(''));
  it('libellé visite', () =>
    expect(makeWith({ type: 'visit', id: 1 }).confirmDeleteLabel()).toContain('visite'));
  it('libellé action', () =>
    expect(makeWith({ type: 'action', id: 1 }).confirmDeleteLabel()).toContain('action'));
  it('libellé livrable', () =>
    expect(makeWith({ type: 'deliverable', id: 1 }).confirmDeleteLabel()).toContain('livrable'));
  it('libellé site', () =>
    expect(makeWith({ type: 'site', id: 1 }).confirmDeleteLabel()).toContain('site'));
});

// ── confirmDelete setters (deleteVisit/action/deliverable + unlinkSite) ────────

describe('ClientDetailComponent — marquage de suppression', () => {
  function makeComp(): ClientDetailComponent {
    const c = make();
    (c as any).confirmDelete = signal(null);
    return c;
  }

  it('deleteVisit stocke le type visit', () => {
    const c = makeComp();
    c.deleteVisit(3);
    expect(c.confirmDelete()).toEqual({ type: 'visit', id: 3 });
  });
  it('deleteAction stocke le type action', () => {
    const c = makeComp();
    c.deleteAction(4);
    expect(c.confirmDelete()).toEqual({ type: 'action', id: 4 });
  });
  it('deleteDeliverable stocke le type deliverable', () => {
    const c = makeComp();
    c.deleteDeliverable(5);
    expect(c.confirmDelete()).toEqual({ type: 'deliverable', id: 5 });
  });
  it('unlinkSite stocke le type site', () => {
    const c = makeComp();
    c.unlinkSite(6);
    expect(c.confirmDelete()).toEqual({ type: 'site', id: 6 });
  });
});

// ── confirmDeleteConfirm dispatch ──────────────────────────────────────────────

describe('ClientDetailComponent — confirmDeleteConfirm()', () => {
  function makeComp(): ClientDetailComponent {
    const c = make();
    (c as any).clientId = 1;
    (c as any).confirmDelete = signal<unknown>(null);
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('ne fait rien si aucune confirmation en attente', () => {
    const c = makeComp();
    (c as any).rssi = { deleteVisit: vi.fn() };
    c.confirmDeleteConfirm();
    expect((c as any).rssi.deleteVisit).not.toHaveBeenCalled();
  });

  it('déclenche la suppression de visite et réinitialise', () => {
    const c = makeComp();
    (c as any).confirmDelete.set({ type: 'visit', id: 9 });
    (c as any).visits = signal([{ id: 9 }]);
    (c as any).rssi = { deleteVisit: vi.fn().mockReturnValue(of(void 0)) };
    c.confirmDeleteConfirm();
    expect((c as any).rssi.deleteVisit).toHaveBeenCalledWith(1, 9);
    expect(c.confirmDelete()).toBeNull();
    expect(c.visits()).toEqual([]);
  });

  it('déclenche la suppression de site (unlink)', () => {
    const c = makeComp();
    (c as any).confirmDelete.set({ type: 'site', id: 2 });
    (c as any).sites = signal([{ id: 2, url: 'a.com', name: 'A' }]);
    (c as any).unlinkedSites = signal([]);
    (c as any).rssi = { unlinkSite: vi.fn().mockReturnValue(of(void 0)) };
    c.confirmDeleteConfirm();
    expect((c as any).rssi.unlinkSite).toHaveBeenCalledWith(1, 2);
    expect(c.sites()).toEqual([]);
    expect(c.unlinkedSites()).toEqual([{ id: 2, url: 'a.com', name: 'A' }]);
  });
});

// ── newPhishingCampaign ────────────────────────────────────────────────────────

describe('ClientDetailComponent — newPhishingCampaign()', () => {
  function makeComp(): ClientDetailComponent {
    const c = make();
    (c as any).clientId = 1;
    (c as any).client = signal({ id: 1, name: 'ACME' });
    (c as any).creatingCampaign = signal(false);
    (c as any).snack = { open: vi.fn() };
    (c as any).router = { navigate: vi.fn() };
    return c;
  }

  it('ne fait rien sans client', () => {
    const c = makeComp();
    (c as any).client = signal(null);
    (c as any).phishing = { createCampaign: vi.fn() };
    c.newPhishingCampaign();
    expect((c as any).phishing.createCampaign).not.toHaveBeenCalled();
  });

  it('ne relance pas si déjà en création', () => {
    const c = makeComp();
    (c as any).creatingCampaign.set(true);
    (c as any).phishing = { createCampaign: vi.fn() };
    c.newPhishingCampaign();
    expect((c as any).phishing.createCampaign).not.toHaveBeenCalled();
  });

  it('crée la campagne puis navigue vers son édition', () => {
    const c = makeComp();
    (c as any).phishing = { createCampaign: vi.fn().mockReturnValue(of({ id: 42 })) };
    (c as any).rssi = { logActivity: vi.fn().mockReturnValue(of(void 0)) };
    c.newPhishingCampaign();
    expect((c as any).phishing.createCampaign).toHaveBeenCalledWith('Campagne ACME', 'standard', 1);
    expect(c.creatingCampaign()).toBe(false);
    expect((c as any).router.navigate).toHaveBeenCalledWith(['/phishing/campaigns', 42, 'edit']);
  });

  it('affiche une erreur en cas d’échec', () => {
    const c = makeComp();
    (c as any).phishing = {
      createCampaign: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
    };
    c.newPhishingCampaign();
    expect(c.creatingCampaign()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalled();
  });
});

// ── inviteClient ───────────────────────────────────────────────────────────────

describe('ClientDetailComponent — inviteClient()', () => {
  function makeComp(client: unknown): ClientDetailComponent {
    const c = make();
    (c as any).client = signal(client);
    (c as any).inviting = signal(false);
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('ne fait rien sans client', () => {
    const c = makeComp(null);
    (c as any).rssi = { inviteClient: vi.fn() };
    c.inviteClient();
    expect((c as any).rssi.inviteClient).not.toHaveBeenCalled();
  });

  it('exige un email avant invitation', () => {
    const c = makeComp({ id: 1, name: 'A', email: '' });
    (c as any).rssi = { inviteClient: vi.fn() };
    c.inviteClient();
    expect((c as any).rssi.inviteClient).not.toHaveBeenCalled();
    expect((c as any).snack.open).toHaveBeenCalled();
  });

  it('envoie l’invitation quand un email est présent', () => {
    const c = makeComp({ id: 7, name: 'A', email: 'a@b.com' });
    (c as any).rssi = {
      inviteClient: vi.fn().mockReturnValue(of({ email: 'a@b.com', account_created: true })),
    };
    c.inviteClient();
    expect((c as any).rssi.inviteClient).toHaveBeenCalledWith(7);
    expect(c.inviting()).toBe(false);
    expect((c as any).snack.open).toHaveBeenCalled();
  });
});

// ── enableAwareness ────────────────────────────────────────────────────────────

describe('ClientDetailComponent — enableAwareness()', () => {
  function makeComp(): ClientDetailComponent {
    const c = make();
    (c as any).client = signal({ id: 3, name: 'A' });
    (c as any).enablingAwareness = signal(false);
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('ne fait rien sans client', () => {
    const c = makeComp();
    (c as any).client = signal(null);
    (c as any).rssi = { enableAwareness: vi.fn() };
    c.enableAwareness();
    expect((c as any).rssi.enableAwareness).not.toHaveBeenCalled();
  });

  it('active la sensibilisation et met à jour le client', () => {
    const c = makeComp();
    (c as any).rssi = {
      enableAwareness: vi.fn().mockReturnValue(of({ id: 99, already: false })),
    };
    c.enableAwareness();
    expect((c as any).rssi.enableAwareness).toHaveBeenCalledWith(3);
    expect(c.client()?.awareness_organization_id).toBe(99);
    expect(c.enablingAwareness()).toBe(false);
  });
});

// ── linkSite ───────────────────────────────────────────────────────────────────

describe('ClientDetailComponent — linkSite()', () => {
  function makeComp(): ClientDetailComponent {
    const c = make();
    (c as any).clientId = 1;
    (c as any).selectedSiteId = signal<number | null>(null);
    (c as any).sites = signal<unknown[]>([]);
    (c as any).unlinkedSites = signal([{ id: 5, url: 'x.com', name: 'X' }]);
    (c as any).showLinkSitePicker = signal(true);
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('ne fait rien sans site sélectionné', () => {
    const c = makeComp();
    (c as any).rssi = { linkSite: vi.fn() };
    c.linkSite();
    expect((c as any).rssi.linkSite).not.toHaveBeenCalled();
  });

  it('lie le site sélectionné et ferme le picker', () => {
    const c = makeComp();
    (c as any).selectedSiteId.set(5);
    (c as any).rssi = {
      linkSite: vi.fn().mockReturnValue(of({ id: 5, url: 'x.com', name: 'X' })),
    };
    c.linkSite();
    expect((c as any).rssi.linkSite).toHaveBeenCalledWith(1, 5);
    expect(c.sites().length).toBe(1);
    expect(c.unlinkedSites().length).toBe(0);
    expect(c.showLinkSitePicker()).toBe(false);
  });
});

// ── onAddFileChange ────────────────────────────────────────────────────────────

describe('ClientDetailComponent — onAddFileChange()', () => {
  it('stocke le fichier et remplit file_url', () => {
    const c = make();
    (c as any).pendingAddFile = signal<File | null>(null);
    const patch = vi.fn();
    (c as any).addDeliverableForm = { patchValue: patch };
    const file = { name: 'rapport.pdf' } as File;
    c.onAddFileChange({ target: { files: [file] } } as unknown as Event);
    expect(c.pendingAddFile()).toBe(file);
    expect(patch).toHaveBeenCalledWith({ file_url: 'rapport.pdf' });
  });

  it('met null si aucun fichier', () => {
    const c = make();
    (c as any).pendingAddFile = signal<File | null>({ name: 'old' } as File);
    (c as any).addDeliverableForm = { patchValue: vi.fn() };
    c.onAddFileChange({ target: { files: [] } } as unknown as Event);
    expect(c.pendingAddFile()).toBeNull();
  });
});

// ── openDeliverableFile ────────────────────────────────────────────────────────

describe('ClientDetailComponent — openDeliverableFile()', () => {
  function makeComp(): ClientDetailComponent {
    const c = make();
    (c as any).clientId = 1;
    (c as any).snack = { open: vi.fn() };
    return c;
  }

  it('ne fait rien si le livrable n’a pas de fichier', () => {
    const c = makeComp();
    (c as any).rssi = { getDeliverableDownloadUrl: vi.fn() };
    c.openDeliverableFile({ id: 1, file_url: null } as never);
    expect((c as any).rssi.getDeliverableDownloadUrl).not.toHaveBeenCalled();
  });

  it('ouvre l’URL renvoyée dans un nouvel onglet', () => {
    const c = makeComp();
    (c as any).rssi = {
      getDeliverableDownloadUrl: vi.fn().mockReturnValue(of({ url: 'https://dl/x' })),
    };
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    c.openDeliverableFile({ id: 2, file_url: 'key' } as never);
    expect((c as any).rssi.getDeliverableDownloadUrl).toHaveBeenCalledWith(1, 2);
    expect(openSpy).toHaveBeenCalledWith('https://dl/x', '_blank', 'noopener');
    openSpy.mockRestore();
  });
});
