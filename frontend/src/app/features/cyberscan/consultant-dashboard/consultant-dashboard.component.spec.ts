import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ConsultantDashboardComponent } from './consultant-dashboard.component';

function make(): ConsultantDashboardComponent {
  return Object.create(ConsultantDashboardComponent.prototype) as ConsultantDashboardComponent;
}

// ── formulaLabel ──────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — formulaLabel()', () => {
  it('retourne "Essentiel" pour essentiel', () =>
    expect(make().formulaLabel('essentiel')).toBe('Essentiel'));
  it('retourne "Premium" pour premium', () =>
    expect(make().formulaLabel('premium')).toBe('Premium'));
  it('retourne "Excellence" pour excellence', () =>
    expect(make().formulaLabel('excellence')).toBe('Excellence'));
  it('retourne "—" pour null', () => expect(make().formulaLabel(null)).toBe('—'));
  it('retourne "—" pour valeur inconnue', () => expect(make().formulaLabel('unknown')).toBe('—'));
});

// ── formulaClass ──────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — formulaClass()', () => {
  it('contient blue pour essentiel', () =>
    expect(make().formulaClass('essentiel')).toContain('blue'));
  it('contient purple pour premium', () =>
    expect(make().formulaClass('premium')).toContain('purple'));
  it('contient amber pour excellence', () =>
    expect(make().formulaClass('excellence')).toContain('amber'));
  it('retourne classe gray pour null', () => expect(make().formulaClass(null)).toContain('gray'));
});

// ── clientStatusClass ─────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — clientStatusClass()', () => {
  it('contient green pour active', () =>
    expect(make().clientStatusClass('active')).toContain('green'));
  it('contient yellow pour inactive', () =>
    expect(make().clientStatusClass('inactive')).toContain('yellow'));
  it('contient red pour churned', () =>
    expect(make().clientStatusClass('churned')).toContain('red'));
  it('retourne classe gray pour inconnu', () =>
    expect(make().clientStatusClass('other')).toContain('gray'));
});

// ── statusColor ───────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — statusColor()', () => {
  it('contient green pour OK', () => expect(make().statusColor('OK')).toContain('green'));
  it('contient yellow pour WARNING', () =>
    expect(make().statusColor('WARNING')).toContain('yellow'));
  it('contient red pour CRITICAL', () => expect(make().statusColor('CRITICAL')).toContain('red'));
  it('retourne classe gray pour null', () => expect(make().statusColor(null)).toContain('gray'));
});

// ── statusIcon ────────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — statusIcon()', () => {
  it('retourne verified_user pour OK', () => expect(make().statusIcon('OK')).toBe('verified_user'));
  it('retourne warning pour WARNING', () => expect(make().statusIcon('WARNING')).toBe('warning'));
  it('retourne gpp_bad pour CRITICAL', () => expect(make().statusIcon('CRITICAL')).toBe('gpp_bad'));
  it('retourne help_outline pour null', () => expect(make().statusIcon(null)).toBe('help_outline'));
});

// ── alertSeverityClass ────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — alertSeverityClass()', () => {
  it('contient red pour critical', () =>
    expect(make().alertSeverityClass('critical')).toContain('red'));
  it('contient orange pour high', () =>
    expect(make().alertSeverityClass('high')).toContain('orange'));
  it('contient yellow pour medium', () =>
    expect(make().alertSeverityClass('medium')).toContain('yellow'));
});

// ── alertIconColor ────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — alertIconColor()', () => {
  it('contient red pour critical', () =>
    expect(make().alertIconColor('critical')).toContain('red'));
  it('contient orange pour high', () => expect(make().alertIconColor('high')).toContain('orange'));
  it('contient yellow pour medium', () =>
    expect(make().alertIconColor('medium')).toContain('yellow'));
});

// ── suggestionIcon ────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — suggestionIcon()', () => {
  it('retourne trending_up pour upsell_opportunity', () =>
    expect(make().suggestionIcon('upsell_opportunity')).toBe('trending_up'));
  it('retourne notification_important pour engagement_alert', () =>
    expect(make().suggestionIcon('engagement_alert')).toBe('notification_important'));
  it('retourne event_available pour renewal_upcoming', () =>
    expect(make().suggestionIcon('renewal_upcoming')).toBe('event_available'));
  it('retourne assignment_late pour high_overdue', () =>
    expect(make().suggestionIcon('high_overdue')).toBe('assignment_late'));
  it('retourne lightbulb pour type inconnu', () =>
    expect(make().suggestionIcon('other')).toBe('lightbulb'));
});

// ── visitTypeLabel ────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — visitTypeLabel()', () => {
  it('retourne "Mensuelle" pour monthly', () =>
    expect(make().visitTypeLabel('monthly')).toBe('Mensuelle'));
  it('retourne "Trimestrielle" pour quarterly', () =>
    expect(make().visitTypeLabel('quarterly')).toBe('Trimestrielle'));
  it('retourne "Annuelle" pour annual', () =>
    expect(make().visitTypeLabel('annual')).toBe('Annuelle'));
  it('retourne "Urgente" pour urgent', () =>
    expect(make().visitTypeLabel('urgent')).toBe('Urgente'));
  it('retourne la valeur brute pour inconnu', () =>
    expect(make().visitTypeLabel('other')).toBe('other'));
});

// ── locationLabel ─────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — locationLabel()', () => {
  it('retourne "Sur site" pour onsite', () =>
    expect(make().locationLabel('onsite')).toBe('Sur site'));
  it('retourne "À distance" pour remote', () =>
    expect(make().locationLabel('remote')).toBe('À distance'));
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("retourne une date contenant l'année", () => {
    const result = make().formatDate('2024-03-15T10:00:00Z');
    expect(result).toContain('2024');
  });
});

// ── formatAmount ──────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — formatAmount()', () => {
  it('retourne "—" pour null', () => expect(make().formatAmount(null)).toBe('—'));
  it('contient € pour un montant valide', () => expect(make().formatAmount(1500)).toContain('€'));
  it('contient 1 500 pour 1500', () => expect(make().formatAmount(1500)).toContain('500'));
});

// ── statusBgClass ─────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — statusBgClass()', () => {
  it('contient green pour OK', () => expect(make().statusBgClass('OK')).toContain('green'));
  it('contient yellow pour WARNING', () =>
    expect(make().statusBgClass('WARNING')).toContain('yellow'));
  it('contient red pour CRITICAL', () => expect(make().statusBgClass('CRITICAL')).toContain('red'));
  it('retourne classe gray pour null', () => expect(make().statusBgClass(null)).toContain('gray'));
});

// ── statusLabel ───────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — statusLabel()', () => {
  it('retourne le statut brut quand présent', () =>
    expect(make().statusLabel('CRITICAL')).toBe('CRITICAL'));
  it('retourne "Aucun scan" pour null', () => expect(make().statusLabel(null)).toBe('Aucun scan'));
});

// ── orgLinkedClientName ───────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — orgLinkedClientName()', () => {
  it('retourne le nom du client lié à une organisation', () => {
    const c = make();
    (c as any).clients = signal([
      { id: 1, name: 'Acme', awareness_organization_id: 42 },
      { id: 2, name: 'Globex', awareness_organization_id: 99 },
    ]);
    expect(c.orgLinkedClientName(42)).toBe('Acme');
  });

  it('retourne null si aucune organisation ne correspond', () => {
    const c = make();
    (c as any).clients = signal([{ id: 1, name: 'Acme', awareness_organization_id: 42 }]);
    expect(c.orgLinkedClientName(7)).toBeNull();
  });

  it('retourne null pour une liste vide', () => {
    const c = make();
    (c as any).clients = signal([]);
    expect(c.orgLinkedClientName(1)).toBeNull();
  });
});

// ── getters MRR & compteurs de statut ─────────────────────────────────────────

describe('ConsultantDashboardComponent — totalMrr', () => {
  it('additionne les montants des clients actifs', () => {
    const c = make();
    (c as any).clients = signal([
      { status: 'active', monthly_amount: 100 },
      { status: 'active', monthly_amount: 250 },
      { status: 'inactive', monthly_amount: 999 },
      { status: 'active', monthly_amount: null },
    ]);
    expect(c.totalMrr).toBe(350);
  });

  it('retourne 0 quand aucun client actif', () => {
    const c = make();
    (c as any).clients = signal([{ status: 'churned', monthly_amount: 100 }]);
    expect(c.totalMrr).toBe(0);
  });

  it('retourne 0 pour une liste vide', () => {
    const c = make();
    (c as any).clients = signal([]);
    expect(c.totalMrr).toBe(0);
  });
});

describe('ConsultantDashboardComponent — compteurs de statut', () => {
  function makeWithClients() {
    const c = make();
    (c as any).clients = signal([
      { worst_status: 'CRITICAL' },
      { worst_status: 'CRITICAL' },
      { worst_status: 'WARNING' },
      { worst_status: 'OK' },
      { worst_status: null },
    ]);
    return c;
  }

  it('criticalCount compte les CRITICAL', () => expect(makeWithClients().criticalCount).toBe(2));
  it('warningCount compte les WARNING', () => expect(makeWithClients().warningCount).toBe(1));
  it('okCount compte les OK', () => expect(makeWithClients().okCount).toBe(1));
});

// ── clearFocus ────────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — clearFocus()', () => {
  it('réinitialise le client ciblé', () => {
    const c = make();
    (c as any).focusedClientId = signal<number | null>(5);
    (c as any).focusedClientName = signal<string | null>('Acme');
    c.clearFocus();
    expect(c.focusedClientId()).toBeNull();
    expect(c.focusedClientName()).toBeNull();
  });
});

// ── onClientRowClick ──────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — onClientRowClick()', () => {
  it('navigue vers le détail du client', () => {
    const c = make();
    const navigate = vi.fn();
    (c as any).router = { navigate };
    c.onClientRowClick({ id: 12 });
    expect(navigate).toHaveBeenCalledWith(['/consultant/clients', 12]);
  });
});

// ── startEdit / cancelEdit ────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — startEdit()', () => {
  it("mémorise l'id et patche le formulaire", () => {
    const c = make();
    (c as any).editingId = signal<number | null>(null);
    const patchValue = vi.fn();
    (c as any).editForm = { patchValue };
    c.startEdit({
      id: 3,
      name: 'Acme',
      email: null,
      description: null,
      formula: 'premium',
      monthly_amount: 500,
      contract_renewal_at: null,
      status: 'active',
    } as any);
    expect(c.editingId()).toBe(3);
    expect(patchValue).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Acme', formula: 'premium', status: 'active' })
    );
  });

  it('remplace les valeurs nulles par des chaînes vides', () => {
    const c = make();
    (c as any).editingId = signal<number | null>(null);
    const patchValue = vi.fn();
    (c as any).editForm = { patchValue };
    c.startEdit({
      id: 4,
      name: 'X',
      email: null,
      description: null,
      formula: null,
      monthly_amount: null,
      contract_renewal_at: null,
      status: 'inactive',
    } as any);
    expect(patchValue).toHaveBeenCalledWith(
      expect.objectContaining({ email: '', description: '', formula: '', contract_renewal_at: '' })
    );
  });
});

describe('ConsultantDashboardComponent — cancelEdit()', () => {
  it("réinitialise l'édition", () => {
    const c = make();
    (c as any).editingId = signal<number | null>(9);
    const reset = vi.fn();
    (c as any).editForm = { reset };
    c.cancelEdit();
    expect(c.editingId()).toBeNull();
    expect(reset).toHaveBeenCalled();
  });
});

// ── addClient ─────────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — addClient()', () => {
  it('ne fait rien si le formulaire est invalide', () => {
    const c = make();
    (c as any).addForm = { invalid: true };
    const createClient = vi.fn();
    (c as any).rssi = { createClient };
    c.addClient();
    expect(createClient).not.toHaveBeenCalled();
  });

  it('crée le client, notifie et recharge en cas de succès', () => {
    const c = make();
    const reset = vi.fn();
    (c as any).addForm = {
      invalid: false,
      getRawValue: () => ({
        name: 'Acme',
        email: '',
        description: '',
        formula: '',
        monthly_amount: null,
        contract_renewal_at: '',
      }),
      reset,
    };
    (c as any).saving = signal(false);
    (c as any).showAddForm = signal(true);
    const open = vi.fn();
    (c as any).snack = { open };
    (c as any).rssi = { createClient: vi.fn().mockReturnValue(of({ name: 'Acme' })) };
    const loadAll = vi.fn();
    (c as any)._loadAll = loadAll;
    c.addClient();
    expect(reset).toHaveBeenCalled();
    expect(c.showAddForm()).toBe(false);
    expect(c.saving()).toBe(false);
    expect(open).toHaveBeenCalledWith(expect.stringContaining('Acme'), 'OK', expect.anything());
    expect(loadAll).toHaveBeenCalled();
  });

  it("affiche l'erreur serveur en cas d'échec", () => {
    const c = make();
    (c as any).addForm = {
      invalid: false,
      getRawValue: () => ({
        name: 'Acme',
        email: '',
        description: '',
        formula: '',
        monthly_amount: null,
        contract_renewal_at: '',
      }),
      reset: vi.fn(),
    };
    (c as any).saving = signal(true);
    (c as any).showAddForm = signal(true);
    const open = vi.fn();
    (c as any).snack = { open };
    (c as any).rssi = {
      createClient: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'Boom' } }))),
    };
    c.addClient();
    expect(c.saving()).toBe(false);
    expect(open).toHaveBeenCalledWith('Boom', 'Fermer', expect.anything());
  });
});

// ── saveEdit ──────────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — saveEdit()', () => {
  it('ne fait rien si le formulaire est invalide', () => {
    const c = make();
    (c as any).editForm = { invalid: true };
    const updateClient = vi.fn();
    (c as any).rssi = { updateClient };
    c.saveEdit(1);
    expect(updateClient).not.toHaveBeenCalled();
  });

  it('met à jour le client, notifie et recharge en cas de succès', () => {
    const c = make();
    (c as any).editForm = {
      invalid: false,
      getRawValue: () => ({
        name: 'Acme',
        email: '',
        description: '',
        formula: '',
        monthly_amount: null,
        contract_renewal_at: '',
        status: '',
      }),
    };
    (c as any).editingId = signal<number | null>(5);
    const open = vi.fn();
    (c as any).snack = { open };
    (c as any).rssi = { updateClient: vi.fn().mockReturnValue(of({})) };
    const loadAll = vi.fn();
    (c as any)._loadAll = loadAll;
    c.saveEdit(5);
    expect(c.editingId()).toBeNull();
    expect(open).toHaveBeenCalledWith('Client mis à jour', 'OK', expect.anything());
    expect(loadAll).toHaveBeenCalled();
  });
});

// ── deleteClient ──────────────────────────────────────────────────────────────

describe('ConsultantDashboardComponent — deleteClient()', () => {
  it('supprime le client, notifie et recharge en cas de succès', () => {
    const c = make();
    (c as any).deletingId = signal<number | null>(null);
    const open = vi.fn();
    (c as any).snack = { open };
    (c as any).rssi = { deleteClient: vi.fn().mockReturnValue(of(void 0)) };
    const loadAll = vi.fn();
    (c as any)._loadAll = loadAll;
    c.deleteClient({ id: 8, name: 'Acme' } as any);
    expect(c.deletingId()).toBeNull();
    expect(open).toHaveBeenCalledWith(expect.stringContaining('Acme'), 'OK', expect.anything());
    expect(loadAll).toHaveBeenCalled();
  });

  it("affiche l'erreur serveur en cas d'échec", () => {
    const c = make();
    (c as any).deletingId = signal<number | null>(8);
    const open = vi.fn();
    (c as any).snack = { open };
    (c as any).rssi = {
      deleteClient: vi.fn().mockReturnValue(throwError(() => ({ error: { detail: 'Nope' } }))),
    };
    c.deleteClient({ id: 8, name: 'Acme' } as any);
    expect(c.deletingId()).toBeNull();
    expect(open).toHaveBeenCalledWith('Nope', 'Fermer', expect.anything());
  });
});
