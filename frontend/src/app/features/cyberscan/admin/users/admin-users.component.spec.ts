import { describe, it, expect, beforeEach } from 'vitest';
import { signal, computed } from '@angular/core';
import { AdminUsersComponent } from './admin-users.component';

interface AdminUser {
  id: number;
  email: string;
  is_active: boolean;
  plan: string;
  plan_name: string | null;
  subscription_status: string | null;
  subscription_since: string | null;
}

function make(): AdminUsersComponent {
  const comp = Object.create(AdminUsersComponent.prototype) as AdminUsersComponent;
  (comp as any).users = signal<AdminUser[]>([]);
  (comp as any).loading = signal(true);
  (comp as any).search = signal('');
  (comp as any).savingPlan = signal<Set<number>>(new Set());
  (comp as any).assignablePlans = [
    { value: 'free', label: 'Gratuit' },
    { value: 'starter', label: 'Starter' },
    { value: 'pro', label: 'Pro' },
    { value: 'business', label: 'Business' },
  ];
  (comp as any).filtered = computed(() => {
    const q = (comp as any).search().toLowerCase();
    return q
      ? (comp as any).users().filter((u: AdminUser) => u.email.toLowerCase().includes(q))
      : (comp as any).users();
  });
  (comp as any).planCounts = computed(() => {
    const counts: Record<string, number> = { free: 0, starter: 0, pro: 0, business: 0 };
    for (const u of (comp as any).users()) {
      const k = u.plan_name ?? 'free';
      counts[k] = (counts[k] ?? 0) + 1;
    }
    return counts;
  });
  return comp;
}

const USERS: AdminUser[] = [
  {
    id: 1,
    email: 'alice@example.com',
    is_active: true,
    plan: 'Pro',
    plan_name: 'pro',
    subscription_status: 'active',
    subscription_since: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    email: 'bob@example.com',
    is_active: false,
    plan: 'Gratuit',
    plan_name: null,
    subscription_status: null,
    subscription_since: null,
  },
  {
    id: 3,
    email: 'carol@starter.io',
    is_active: true,
    plan: 'Starter',
    plan_name: 'starter',
    subscription_status: 'active',
    subscription_since: '2024-06-01T00:00:00Z',
  },
];

// ── planColor ──────────────────────────────────────────────────────────────────

describe('AdminUsersComponent — planColor()', () => {
  it('retourne les classes pro pour plan pro', () => {
    const comp = make();
    expect(comp.planColor('pro')).toContain('purple');
  });

  it('retourne les classes starter pour plan starter', () => {
    const comp = make();
    expect(comp.planColor('starter')).toContain('blue');
  });

  it('retourne les classes business pour plan business', () => {
    const comp = make();
    expect(comp.planColor('business')).toContain('orange');
  });

  it('retourne les classes grises pour plan inconnu', () => {
    const comp = make();
    expect(comp.planColor(null)).toContain('gray');
    expect(comp.planColor('unknown')).toContain('gray');
  });
});

// ── planCounts ─────────────────────────────────────────────────────────────────

describe('AdminUsersComponent — planCounts()', () => {
  it('retourne des zéros avec une liste vide', () => {
    const comp = make();
    const counts = (comp as any).planCounts();
    expect(counts.free).toBe(0);
    expect(counts.pro).toBe(0);
  });

  it('compte correctement les utilisateurs par plan', () => {
    const comp = make();
    (comp as any).users.set(USERS);
    const counts = (comp as any).planCounts();
    expect(counts.pro).toBe(1);
    expect(counts.starter).toBe(1);
    expect(counts.free).toBe(1);
  });

  it('compte null plan_name comme free', () => {
    const comp = make();
    (comp as any).users.set([
      {
        id: 1,
        email: 'x@x.com',
        is_active: true,
        plan: 'Gratuit',
        plan_name: null,
        subscription_status: null,
        subscription_since: null,
      },
    ]);
    expect((comp as any).planCounts().free).toBe(1);
  });
});

// ── filtered ──────────────────────────────────────────────────────────────────

describe('AdminUsersComponent — filtered()', () => {
  it('retourne tous les utilisateurs sans filtre', () => {
    const comp = make();
    (comp as any).users.set(USERS);
    expect((comp as any).filtered().length).toBe(3);
  });

  it('filtre par email (insensible à la casse)', () => {
    const comp = make();
    (comp as any).users.set(USERS);
    (comp as any).search.set('ALICE');
    expect((comp as any).filtered().length).toBe(1);
    expect((comp as any).filtered()[0].email).toBe('alice@example.com');
  });

  it('retourne une liste vide si aucun email ne correspond', () => {
    const comp = make();
    (comp as any).users.set(USERS);
    (comp as any).search.set('zzz');
    expect((comp as any).filtered().length).toBe(0);
  });

  it('filtre sur un domaine commun', () => {
    const comp = make();
    (comp as any).users.set(USERS);
    (comp as any).search.set('example');
    expect((comp as any).filtered().length).toBe(2);
  });
});

// ── setPlan / isSavingPlan ──────────────────────────────────────────────────────

describe('AdminUsersComponent — setPlan()', () => {
  function withHttp(comp: AdminUsersComponent, response: unknown) {
    (comp as any).http = {
      patch: () => ({
        subscribe: (obs: { next: (r: unknown) => void }) => obs.next(response),
      }),
    };
    (comp as any).auth = { headers: () => ({}) };
  }

  it('attribue un nouveau plan et met à jour la ligne', () => {
    const comp = make();
    (comp as any).users.set([USERS[1]]); // bob, plan_name null (gratuit)
    withHttp(comp, { id: 2, plan: 'Pro', plan_name: 'pro' });
    comp.setPlan(USERS[1] as any, 'pro');
    const bob = (comp as any).users()[0];
    expect(bob.plan_name).toBe('pro');
    expect(bob.plan).toBe('Pro');
    expect(bob.subscription_status).toBe('active');
    expect(comp.isSavingPlan(2)).toBe(false);
  });

  it('ne fait rien si le plan choisi est déjà le plan courant', () => {
    const comp = make();
    let called = false;
    (comp as any).http = {
      patch: () => {
        called = true;
        return { subscribe: () => {} };
      },
    };
    comp.setPlan(USERS[0] as any, 'pro'); // alice est déjà pro
    expect(called).toBe(false);
  });

  it('ne fait rien si un enregistrement est déjà en cours pour cet utilisateur', () => {
    const comp = make();
    (comp as any).savingPlan.set(new Set([1]));
    let called = false;
    (comp as any).http = {
      patch: () => {
        called = true;
        return { subscribe: () => {} };
      },
    };
    comp.setPlan(USERS[0] as any, 'business');
    expect(called).toBe(false);
  });

  it('libère le drapeau de sauvegarde en cas d’erreur', () => {
    const comp = make();
    (comp as any).users.set([USERS[1]]);
    (comp as any).http = {
      patch: () => ({
        subscribe: (obs: { error: () => void }) => obs.error(),
      }),
    };
    (comp as any).auth = { headers: () => ({}) };
    comp.setPlan(USERS[1] as any, 'pro');
    expect(comp.isSavingPlan(2)).toBe(false);
  });
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('AdminUsersComponent — formatDate()', () => {
  it('retourne un tiret si iso est null', () => {
    const comp = make();
    expect(comp.formatDate(null)).toBe('—');
  });

  it('retourne une chaîne non vide pour une date valide', () => {
    const comp = make();
    const result = comp.formatDate('2024-01-15T10:00:00Z');
    expect(result.length).toBeGreaterThan(0);
    expect(result).not.toBe('—');
  });

  it("contient l'année pour une date ISO valide", () => {
    const comp = make();
    expect(comp.formatDate('2024-06-01T00:00:00Z')).toContain('2024');
  });
});
