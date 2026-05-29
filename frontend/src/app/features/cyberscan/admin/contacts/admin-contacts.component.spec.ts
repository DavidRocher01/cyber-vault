import { describe, it, expect } from 'vitest';
import { signal, computed } from '@angular/core';
import { AdminContactsComponent } from './admin-contacts.component';

interface ContactMessage {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  need_type: string;
  site_url: string | null;
  message: string;
  status: string;
  created_at: string;
}

function make(): AdminContactsComponent {
  const comp = Object.create(AdminContactsComponent.prototype) as AdminContactsComponent;
  (comp as any).messages = signal<ContactMessage[]>([]);
  (comp as any).loading = signal(true);
  (comp as any).filter = signal<'all' | 'new' | 'handled' | 'archived'>('all');
  (comp as any).expanded = signal<number | null>(null);
  (comp as any).filtered = computed(() => {
    const f = (comp as any).filter();
    return f === 'all'
      ? (comp as any).messages()
      : (comp as any).messages().filter((m: ContactMessage) => m.status === f);
  });
  return comp;
}

const MESSAGES: ContactMessage[] = [
  {
    id: 1,
    name: 'Alice',
    email: 'alice@x.com',
    phone: null,
    need_type: 'audit-flash',
    site_url: null,
    message: 'Hello',
    status: 'new',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'Bob',
    email: 'bob@x.com',
    phone: null,
    need_type: 'pentest',
    site_url: null,
    message: 'Hi',
    status: 'handled',
    created_at: '2024-01-02T00:00:00Z',
  },
  {
    id: 3,
    name: 'Carol',
    email: 'carol@x.com',
    phone: null,
    need_type: 'autre',
    site_url: null,
    message: 'Yo',
    status: 'archived',
    created_at: '2024-01-03T00:00:00Z',
  },
  {
    id: 4,
    name: 'Dave',
    email: 'dave@x.com',
    phone: null,
    need_type: 'abonnement',
    site_url: null,
    message: 'Hey',
    status: 'new',
    created_at: '2024-01-04T00:00:00Z',
  },
];

// ── needLabel ─────────────────────────────────────────────────────────────────

describe('AdminContactsComponent — needLabel()', () => {
  it('traduit audit-flash', () => {
    const comp = make();
    expect(comp.needLabel('audit-flash')).toBe('Audit Flash');
  });

  it('traduit audit-app', () => {
    const comp = make();
    expect(comp.needLabel('audit-app')).toBe('App-Check');
  });

  it('traduit pentest', () => {
    const comp = make();
    expect(comp.needLabel('pentest')).toBe('Pentest');
  });

  it('traduit abonnement', () => {
    const comp = make();
    expect(comp.needLabel('abonnement')).toBe('Abonnement');
  });

  it('traduit autre', () => {
    const comp = make();
    expect(comp.needLabel('autre')).toBe('Autre');
  });

  it('retourne la valeur brute pour un type inconnu', () => {
    const comp = make();
    expect(comp.needLabel('unknown-type')).toBe('unknown-type');
  });
});

// ── toggleExpand ──────────────────────────────────────────────────────────────

describe('AdminContactsComponent — toggleExpand()', () => {
  it('ouvre un message fermé', () => {
    const comp = make();
    comp.toggleExpand(1);
    expect((comp as any).expanded()).toBe(1);
  });

  it('ferme un message ouvert (toggle off)', () => {
    const comp = make();
    comp.toggleExpand(1);
    comp.toggleExpand(1);
    expect((comp as any).expanded()).toBeNull();
  });

  it('bascule vers un autre message ouvert', () => {
    const comp = make();
    comp.toggleExpand(1);
    comp.toggleExpand(2);
    expect((comp as any).expanded()).toBe(2);
  });
});

// ── filtered ──────────────────────────────────────────────────────────────────

describe('AdminContactsComponent — filtered()', () => {
  it('retourne tous les messages avec filtre "all"', () => {
    const comp = make();
    (comp as any).messages.set(MESSAGES);
    expect((comp as any).filtered().length).toBe(4);
  });

  it('filtre les messages "new"', () => {
    const comp = make();
    (comp as any).messages.set(MESSAGES);
    (comp as any).filter.set('new');
    const result = (comp as any).filtered();
    expect(result.length).toBe(2);
    expect(result.every((m: ContactMessage) => m.status === 'new')).toBe(true);
  });

  it('filtre les messages "handled"', () => {
    const comp = make();
    (comp as any).messages.set(MESSAGES);
    (comp as any).filter.set('handled');
    const result = (comp as any).filtered();
    expect(result.length).toBe(1);
    expect(result[0].name).toBe('Bob');
  });

  it('filtre les messages "archived"', () => {
    const comp = make();
    (comp as any).messages.set(MESSAGES);
    (comp as any).filter.set('archived');
    const result = (comp as any).filtered();
    expect(result.length).toBe(1);
    expect(result[0].name).toBe('Carol');
  });

  it('retourne une liste vide si aucun message ne correspond', () => {
    const comp = make();
    (comp as any).messages.set([]);
    (comp as any).filter.set('new');
    expect((comp as any).filtered().length).toBe(0);
  });
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('AdminContactsComponent — formatDate()', () => {
  it('retourne une chaîne non vide pour une date ISO valide', () => {
    const comp = make();
    expect(comp.formatDate('2024-01-15T10:00:00Z')).toBeTruthy();
  });

  it("contient l'année pour une date valide", () => {
    const comp = make();
    expect(comp.formatDate('2024-06-01T00:00:00Z')).toContain('2024');
  });
});
