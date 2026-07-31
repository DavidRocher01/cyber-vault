/**
 * Nis2Component — tests unitaires complets.
 *
 * Couvre :
 *  - Helpers purs (statusLabel, statusIcon, statusClass, scoreColor, scoreLabel, formatDate)
 *  - Logique signal (getStatus, toggle, setStatus, recalcScore, resetAll)
 *  - Compteurs réactifs (compliantCount, partialCount, ncCount, naCount, totalItems)
 *  - Agrégats par catégorie (catCompliance, catScore)
 *  - Getter _fullItems (34 items complets)
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { signal, computed } from '@angular/core';
import { of, throwError } from 'rxjs';
import { Nis2Component, Nis2Category, Nis2Status } from './nis2.component';

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Crée un composant avec ses signals initialisés, sans Angular DI. */
function make(): Nis2Component {
  const c = Object.create(Nis2Component.prototype) as Nis2Component;

  // Signals d'état
  (c as any).loading = signal(false);
  (c as any).saving = signal(false);
  (c as any).exporting = signal(false);
  (c as any).exportingAuditor = signal(false);
  (c as any).score = signal(0);
  // Mesures detenues par la plateforme (preuve de formation) — vide par defaut.
  (c as any).preuves = signal({});
  (c as any).updatedAt = signal<string | null>(null);

  // Gating export payant
  (c as any).subLoaded = signal(false);
  (c as any).canExport = signal(false);
  (c as any).showUpgrade = computed(() => (c as any).subLoaded() && !(c as any).canExport());
  (c as any).billing = { getMySubscription: vi.fn().mockReturnValue(of(null)) };
  (c as any).router = { navigate: vi.fn() };

  // Données
  (c as any).categories = signal<Nis2Category[]>([]);
  (c as any).items = signal<Record<string, Nis2Status>>({});

  // Constantes
  (c as any).CYCLE = ['non_compliant', 'partial', 'compliant', 'na'];
  (c as any).STATUS_LIST = ['compliant', 'partial', 'non_compliant', 'na'];

  // Computed signals (reproduit la logique du composant)
  (c as any).allItemIds = computed(() =>
    (c as any).categories().flatMap((cat: Nis2Category) => cat.items.map(i => i.id))
  );
  (c as any).totalItems = computed(() =>
    (c as any).categories().reduce((s: number, cat: Nis2Category) => s + cat.items.length, 0)
  );
  (c as any).compliantCount = computed(
    () => (c as any).allItemIds().filter((id: string) => c.getStatus(id) === 'compliant').length
  );
  (c as any).partialCount = computed(
    () => (c as any).allItemIds().filter((id: string) => c.getStatus(id) === 'partial').length
  );
  (c as any).ncCount = computed(
    () => (c as any).allItemIds().filter((id: string) => c.getStatus(id) === 'non_compliant').length
  );
  (c as any).naCount = computed(
    () => (c as any).allItemIds().filter((id: string) => c.getStatus(id) === 'na').length
  );

  return c;
}

/** Catégorie de test avec N items. */
function makeCat(id: string, itemCount: number): Nis2Category {
  return {
    id,
    label: `Cat ${id}`,
    icon: 'shield',
    items: Array.from({ length: itemCount }, (_, i) => ({
      id: `${id}_item${i}`,
      label: `Item ${i}`,
      desc: `Desc ${i}`,
    })),
  };
}

/** Composant avec des catégories de test préchargées. */
function makeWithCats(...counts: number[]): Nis2Component {
  const c = make();
  const cats = counts.map((n, i) => makeCat(`cat${i}`, n));
  (c as any).categories.set(cats);
  return c;
}

// ── statusLabel() ─────────────────────────────────────────────────────────────

describe('statusLabel()', () => {
  const c = make();
  it('compliant → Conforme', () => expect(c.statusLabel('compliant')).toBe('Conforme'));
  it('partial → Partiel', () => expect(c.statusLabel('partial')).toBe('Partiel'));
  it('non_compliant → Non conforme', () =>
    expect(c.statusLabel('non_compliant')).toBe('Non conforme'));
  it('na → N/A', () => expect(c.statusLabel('na')).toBe('N/A'));
  it('inconnu → valeur brute', () => expect(c.statusLabel('foo')).toBe('foo'));
});

// ── statusIcon() ──────────────────────────────────────────────────────────────

describe('statusIcon()', () => {
  const c = make();
  it('compliant → check_circle', () => expect(c.statusIcon('compliant')).toBe('check_circle'));
  it('partial → pending', () => expect(c.statusIcon('partial')).toBe('pending'));
  it('non_compliant → cancel', () => expect(c.statusIcon('non_compliant')).toBe('cancel'));
  it('na → remove_circle_outline', () => expect(c.statusIcon('na')).toBe('remove_circle_outline'));
  it('inconnu → help_outline', () => expect(c.statusIcon('?')).toBe('help_outline'));
});

// ── statusClass() ─────────────────────────────────────────────────────────────

describe('statusClass()', () => {
  const c = make();
  it('compliant contient green', () => expect(c.statusClass('compliant')).toContain('green'));
  it('partial contient yellow', () => expect(c.statusClass('partial')).toContain('yellow'));
  it('non_compliant contient red', () => expect(c.statusClass('non_compliant')).toContain('red'));
  it('na contient gray', () => expect(c.statusClass('na')).toContain('gray'));
  it('inconnu → fallback gray', () => expect(c.statusClass('?')).toContain('gray'));
});

// ── statusColor() ─────────────────────────────────────────────────────────────

describe('statusColor()', () => {
  const c = make();
  it('compliant → #4ade80', () => expect(c.statusColor('compliant')).toBe('#4ade80'));
  it('partial → #facc15', () => expect(c.statusColor('partial')).toBe('#facc15'));
  it('non_compliant → #f87171', () => expect(c.statusColor('non_compliant')).toBe('#f87171'));
  it('na → #6b7280', () => expect(c.statusColor('na')).toBe('#6b7280'));
  it('inconnu → #6b7280', () => expect(c.statusColor('?')).toBe('#6b7280'));
});

// ── scoreColor() ──────────────────────────────────────────────────────────────

describe('scoreColor()', () => {
  const c = make();
  it('>= 80 → vert', () => expect(c.scoreColor(80)).toBe('#4ade80'));
  it('100 → vert', () => expect(c.scoreColor(100)).toBe('#4ade80'));
  it('50 → jaune', () => expect(c.scoreColor(50)).toBe('#facc15'));
  it('79 → jaune', () => expect(c.scoreColor(79)).toBe('#facc15'));
  it('49 → rouge', () => expect(c.scoreColor(49)).toBe('#f87171'));
  it('0 → rouge', () => expect(c.scoreColor(0)).toBe('#f87171'));
});

// ── scoreLabel() ──────────────────────────────────────────────────────────────

describe('scoreLabel()', () => {
  const c = make();
  it('>= 80 → Conforme', () => expect(c.scoreLabel(80)).toBe('Conforme'));
  it('50-79 → En cours', () => expect(c.scoreLabel(50)).toBe('En cours'));
  it('79 → En cours', () => expect(c.scoreLabel(79)).toBe('En cours'));
  it('< 50 → Non conforme', () => expect(c.scoreLabel(49)).toBe('Non conforme'));
  it('0 → Non conforme', () => expect(c.scoreLabel(0)).toBe('Non conforme'));
});

// ── formatDate() ──────────────────────────────────────────────────────────────

describe('formatDate()', () => {
  const c = make();
  it('null → "—"', () => expect(c.formatDate(null)).toBe('—'));
  it("ISO → contient l'année", () =>
    expect(c.formatDate('2024-06-15T10:00:00Z')).toContain('2024'));
  it('retourne une string', () =>
    expect(typeof c.formatDate('2025-01-01T00:00:00Z')).toBe('string'));
});

// ── getStatus() ───────────────────────────────────────────────────────────────

describe('getStatus()', () => {
  it('retourne non_compliant par défaut si item absent', () => {
    const c = make();
    expect(c.getStatus('rssi')).toBe('non_compliant');
  });

  it('retourne le statut explicitement défini', () => {
    const c = make();
    (c as any).items.set({ rssi: 'compliant' });
    expect(c.getStatus('rssi')).toBe('compliant');
  });

  it('retourne na si explicitement défini', () => {
    const c = make();
    (c as any).items.set({ rssi: 'na' });
    expect(c.getStatus('rssi')).toBe('na');
  });
});

// ── toggle() ──────────────────────────────────────────────────────────────────

describe('toggle()', () => {
  it('cycle : non_compliant → partial', () => {
    const c = make();
    c.toggle('rssi');
    expect(c.getStatus('rssi')).toBe('partial');
  });

  it('cycle : partial → compliant', () => {
    const c = make();
    (c as any).items.set({ rssi: 'partial' });
    c.toggle('rssi');
    expect(c.getStatus('rssi')).toBe('compliant');
  });

  it('cycle : compliant → na', () => {
    const c = make();
    (c as any).items.set({ rssi: 'compliant' });
    c.toggle('rssi');
    expect(c.getStatus('rssi')).toBe('na');
  });

  it('cycle : na → non_compliant', () => {
    const c = make();
    (c as any).items.set({ rssi: 'na' });
    c.toggle('rssi');
    expect(c.getStatus('rssi')).toBe('non_compliant');
  });

  it("toggle n'affecte pas les autres items", () => {
    const c = make();
    (c as any).items.set({ rssi: 'compliant', policy: 'partial' });
    c.toggle('rssi');
    expect(c.getStatus('policy')).toBe('partial');
  });
});

// ── setStatus() ───────────────────────────────────────────────────────────────

describe('setStatus()', () => {
  it('définit le statut directement', () => {
    const c = make();
    c.setStatus('rssi', 'compliant');
    expect(c.getStatus('rssi')).toBe('compliant');
  });

  it('écrase un statut existant', () => {
    const c = make();
    (c as any).items.set({ rssi: 'partial' });
    c.setStatus('rssi', 'na');
    expect(c.getStatus('rssi')).toBe('na');
  });

  it("n'affecte pas les autres items", () => {
    const c = make();
    (c as any).items.set({ rssi: 'compliant', policy: 'partial' });
    c.setStatus('rssi', 'non_compliant');
    expect(c.getStatus('policy')).toBe('partial');
  });
});

// ── recalcScore() ─────────────────────────────────────────────────────────────

describe('recalcScore()', () => {
  it('score 0 si aucun item (catégories vides)', () => {
    const c = make();
    c.recalcScore();
    expect((c as any).score()).toBe(0);
  });

  it('score 0 si tous non_compliant', () => {
    const c = makeWithCats(2, 2);
    // Items par défaut = non_compliant
    c.recalcScore();
    expect((c as any).score()).toBe(0);
  });

  it('score 100 si tous compliant', () => {
    const c = makeWithCats(2, 2);
    const ids = (c as any).allItemIds();
    (c as any).items.set(Object.fromEntries(ids.map((id: string) => [id, 'compliant'])));
    c.recalcScore();
    expect((c as any).score()).toBe(100);
  });

  it('score 50 si tous partial', () => {
    const c = makeWithCats(2, 2);
    const ids = (c as any).allItemIds();
    (c as any).items.set(Object.fromEntries(ids.map((id: string) => [id, 'partial'])));
    c.recalcScore();
    expect((c as any).score()).toBe(50);
  });

  it('score 0 si tous na (aucun scorable)', () => {
    const c = makeWithCats(2, 2);
    const ids = (c as any).allItemIds();
    (c as any).items.set(Object.fromEntries(ids.map((id: string) => [id, 'na'])));
    c.recalcScore();
    expect((c as any).score()).toBe(0);
  });

  it('na exclu du dénominateur — 1 compliant parmi 1 scorable = 100', () => {
    const c = makeWithCats(2); // 2 items : cat0_item0, cat0_item1
    const [id0, id1] = (c as any).allItemIds();
    (c as any).items.set({ [id0]: 'compliant', [id1]: 'na' });
    c.recalcScore();
    expect((c as any).score()).toBe(100);
  });

  it('items non renseignés comptent comme non_compliant', () => {
    const c = makeWithCats(4); // 4 items
    const [id0] = (c as any).allItemIds();
    (c as any).items.set({ [id0]: 'compliant' }); // 3 autres non renseignés
    c.recalcScore();
    // 2pts / (4*2) * 100 = 25
    expect((c as any).score()).toBe(25);
  });

  it('est appelé automatiquement par toggle', () => {
    const c = makeWithCats(2);
    const [id0, id1] = (c as any).allItemIds();
    // Partir de : id0=partial(1pt), id1=compliant(2pt) → score 75
    (c as any).items.set({ [id0]: 'partial', [id1]: 'compliant' });
    c.recalcScore();
    expect((c as any).score()).toBe(75);

    // Toggle id0 : partial → compliant → tous conformes → 100
    c.toggle(id0);
    expect((c as any).score()).toBe(100);
  });
});

// ── resetAll() ────────────────────────────────────────────────────────────────

describe('resetAll()', () => {
  it('vide le map items', () => {
    const c = make();
    (c as any).items.set({ rssi: 'compliant', policy: 'partial' });
    c.resetAll();
    expect((c as any).items()).toEqual({});
  });

  it('score revient à 0 après reset', () => {
    const c = makeWithCats(4);
    const ids = (c as any).allItemIds();
    (c as any).items.set(Object.fromEntries(ids.map((id: string) => [id, 'compliant'])));
    c.recalcScore();
    expect((c as any).score()).toBe(100);

    c.resetAll();
    expect((c as any).score()).toBe(0);
  });

  it('getStatus retourne non_compliant après reset (pas na)', () => {
    const c = makeWithCats(2);
    const [id0] = (c as any).allItemIds();
    (c as any).items.set({ [id0]: 'compliant' });
    c.resetAll();
    // Map vide → getStatus fallback = non_compliant
    expect(c.getStatus(id0)).toBe('non_compliant');
  });

  it('reset puis 2 conformes ne donne pas 100%', () => {
    const c = makeWithCats(4); // 4 items
    c.resetAll();
    const [id0, id1] = (c as any).allItemIds();
    c.setStatus(id0, 'compliant');
    c.setStatus(id1, 'compliant');
    // 4pts / (4*2) * 100 = 50 (les 2 autres = non_compliant par défaut)
    expect((c as any).score()).toBe(50);
  });
});

// ── Compteurs réactifs ────────────────────────────────────────────────────────

describe('compliantCount / partialCount / ncCount / naCount', () => {
  it('tous 0 avec catégories vides', () => {
    const c = make();
    expect((c as any).compliantCount()).toBe(0);
    expect((c as any).partialCount()).toBe(0);
    expect((c as any).ncCount()).toBe(0);
    expect((c as any).naCount()).toBe(0);
  });

  it('comptent correctement après setStatus', () => {
    // 5 items : on en set 4, le 5ème reste non_compliant par défaut
    const c = makeWithCats(5);
    const [a, b, d, e] = (c as any).allItemIds(); // on n'assigne pas le 5ème
    c.setStatus(a, 'compliant');
    c.setStatus(b, 'compliant');
    c.setStatus(d, 'partial');
    c.setStatus(e, 'na');
    expect((c as any).compliantCount()).toBe(2);
    expect((c as any).partialCount()).toBe(1);
    expect((c as any).ncCount()).toBe(1); // le 5ème item, non renseigné
    expect((c as any).naCount()).toBe(1);
  });

  it('ncCount inclut les items non renseignés (défaut = non_compliant)', () => {
    const c = makeWithCats(3);
    // Aucun item set → tous sont non_compliant par défaut via getStatus()
    expect((c as any).ncCount()).toBe(3);
  });

  it('naCount ne compte pas les items non renseignés', () => {
    const c = makeWithCats(3);
    expect((c as any).naCount()).toBe(0);
  });

  it('naCount + ncCount + compliantCount + partialCount = totalItems', () => {
    const c = makeWithCats(3, 2);
    const [a, b] = (c as any).allItemIds();
    c.setStatus(a, 'compliant');
    c.setStatus(b, 'na');
    const total = (c as any).totalItems();
    const sum =
      (c as any).compliantCount() +
      (c as any).partialCount() +
      (c as any).ncCount() +
      (c as any).naCount();
    expect(sum).toBe(total);
  });

  it('mise à jour réactive après toggle', () => {
    const c = makeWithCats(2);
    const [id0] = (c as any).allItemIds();
    expect((c as any).ncCount()).toBe(2);
    c.toggle(id0); // non_compliant → partial
    expect((c as any).ncCount()).toBe(1);
    expect((c as any).partialCount()).toBe(1);
  });
});

// ── totalItems ────────────────────────────────────────────────────────────────

describe('totalItems', () => {
  it('0 avec aucune catégorie', () => {
    expect((make() as any).totalItems()).toBe(0);
  });

  it('compte tous les items de toutes les catégories', () => {
    const c = makeWithCats(4, 3, 2);
    expect((c as any).totalItems()).toBe(9);
  });
});

// ── catCompliance() ───────────────────────────────────────────────────────────

describe('catCompliance()', () => {
  it('retourne 0 partout si aucun item renseigné', () => {
    const c = make();
    const cat = makeCat('x', 3);
    const r = c.catCompliance(cat);
    expect(r.compliant).toBe(0);
    expect(r.partial).toBe(0);
    expect(r.nc).toBe(3); // défaut non_compliant
    expect(r.total).toBe(3);
  });

  it('compte correctement les statuts mixtes', () => {
    const c = make();
    const cat = makeCat('y', 4);
    (c as any).items.set({
      y_item0: 'compliant',
      y_item1: 'partial',
      y_item2: 'na',
      // y_item3 → non_compliant par défaut
    });
    const r = c.catCompliance(cat);
    expect(r.compliant).toBe(1);
    expect(r.partial).toBe(1);
    expect(r.nc).toBe(1);
    expect(r.total).toBe(4);
  });
});

// ── catScore() ────────────────────────────────────────────────────────────────

describe('catScore()', () => {
  it('retourne 0 si aucun item scorable (tous na)', () => {
    const c = make();
    const cat = makeCat('z', 3);
    (c as any).items.set({
      z_item0: 'na',
      z_item1: 'na',
      z_item2: 'na',
    });
    expect(c.catScore(cat)).toBe(0);
  });

  it('retourne 100 si tous compliant', () => {
    const c = make();
    const cat = makeCat('a', 3);
    (c as any).items.set({
      a_item0: 'compliant',
      a_item1: 'compliant',
      a_item2: 'compliant',
    });
    expect(c.catScore(cat)).toBe(100);
  });

  it('retourne 50 si tous partial', () => {
    const c = make();
    const cat = makeCat('b', 2);
    (c as any).items.set({ b_item0: 'partial', b_item1: 'partial' });
    expect(c.catScore(cat)).toBe(50);
  });

  it('exclut les items na du dénominateur', () => {
    const c = make();
    const cat = makeCat('c', 3);
    (c as any).items.set({
      c_item0: 'compliant',
      c_item1: 'na',
      c_item2: 'na',
    });
    // 1 scorable, 1 compliant → 100%
    expect(c.catScore(cat)).toBe(100);
  });
});

// ── _fullItems getter ────────────────────────────────────────────────────────

describe('_fullItems (getter privé)', () => {
  it('retourne un item pour chaque item des catégories', () => {
    const c = makeWithCats(4, 3);
    const full = (c as any)._fullItems;
    expect(Object.keys(full).length).toBe(7);
  });

  it('items non renseignés → non_compliant dans _fullItems', () => {
    const c = makeWithCats(3);
    const full = (c as any)._fullItems;
    expect(Object.values(full).every(v => v === 'non_compliant')).toBe(true);
  });

  it('items explicitement définis sont conservés', () => {
    const c = makeWithCats(3);
    const [id0] = (c as any).allItemIds();
    (c as any).items.set({ [id0]: 'compliant' });
    const full = (c as any)._fullItems;
    expect(full[id0]).toBe('compliant');
  });

  it('items na sont conservés dans _fullItems', () => {
    const c = makeWithCats(2);
    const [id0, id1] = (c as any).allItemIds();
    (c as any).items.set({ [id0]: 'na', [id1]: 'partial' });
    const full = (c as any)._fullItems;
    expect(full[id0]).toBe('na');
    expect(full[id1]).toBe('partial');
  });

  it('_fullItems après reset contient non_compliant pour tous', () => {
    const c = makeWithCats(4);
    const ids = (c as any).allItemIds();
    (c as any).items.set(Object.fromEntries(ids.map((id: string) => [id, 'compliant'])));
    c.resetAll();
    const full = (c as any)._fullItems;
    expect(Object.values(full).every(v => v === 'non_compliant')).toBe(true);
  });
});

// ── ngOnInit() ────────────────────────────────────────────────────────────────

describe('ngOnInit()', () => {
  it('cas nominal : hydrate categories/items/score/updatedAt et coupe loading', () => {
    const c = make();
    (c as any).loading = signal(true);
    const cat = makeCat('a', 2);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          getNis2Assessment: vi.fn().mockReturnValue(
            of({
              categories: [cat],
              items: { a_item0: 'compliant' },
              score: 42,
              updated_at: '2024-06-15T10:00:00Z',
            })
          ),
        };
    (c as any).snack = { open: vi.fn() };
    c.ngOnInit();
    expect((c as any).categories()).toEqual([cat]);
    expect((c as any).items()).toEqual({ a_item0: 'compliant' });
    expect((c as any).score()).toBe(42);
    expect((c as any).updatedAt()).toBe('2024-06-15T10:00:00Z');
    expect((c as any).loading()).toBe(false);
  });

  it('réponse partielle : applique les valeurs par défaut', () => {
    const c = make();
    (c as any).loading = signal(true);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { getNis2Assessment: vi.fn().mockReturnValue(of({})) };
    (c as any).snack = { open: vi.fn() };
    c.ngOnInit();
    expect((c as any).categories()).toEqual([]);
    expect((c as any).items()).toEqual({});
    expect((c as any).score()).toBe(0);
    expect((c as any).updatedAt()).toBe(null);
    expect((c as any).loading()).toBe(false);
  });

  it('erreur : coupe loading et affiche un snack', () => {
    const c = make();
    (c as any).loading = signal(true);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          getNis2Assessment: vi.fn().mockReturnValue(throwError(() => new Error('boom'))),
        };
    const snack = { open: vi.fn() };
    (c as any).snack = snack;
    c.ngOnInit();
    expect((c as any).loading()).toBe(false);
    expect(snack.open).toHaveBeenCalledWith('Erreur lors du chargement', 'Fermer', {
      duration: 4000,
    });
  });

  it('plan payant : canExport passe à true (pas de CTA upgrade)', () => {
    const c = make();
    (c as any).billing = {
      getMySubscription: vi.fn().mockReturnValue(of({ plan: { allow_conformity_export: true } })),
    };
    (c as any).complianceApi = { getNis2Assessment: vi.fn().mockReturnValue(of({})) };
    (c as any).snack = { open: vi.fn() };
    c.ngOnInit();
    expect((c as any).canExport()).toBe(true);
    expect((c as any).showUpgrade()).toBe(false);
  });

  it('plan Gratuit : canExport reste false et showUpgrade passe à true', () => {
    const c = make();
    (c as any).billing = { getMySubscription: vi.fn().mockReturnValue(of(null)) };
    (c as any).complianceApi = { getNis2Assessment: vi.fn().mockReturnValue(of({})) };
    (c as any).snack = { open: vi.fn() };
    c.ngOnInit();
    expect((c as any).canExport()).toBe(false);
    expect((c as any).showUpgrade()).toBe(true);
  });
});

// ── save() ────────────────────────────────────────────────────────────────────

describe('save()', () => {
  it('cas nominal : envoie _fullItems, met à jour score/updatedAt, snack succès', () => {
    const c = makeWithCats(2);
    (c as any).saving = signal(false);
    const saveMock = vi.fn().mockReturnValue(of({ score: 88, updated_at: '2024-07-01T12:00:00Z' }));
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        { saveNis2Assessment: saveMock };
    const snack = { open: vi.fn() };
    (c as any).snack = snack;
    c.save();
    // _fullItems : 2 items non renseignés → non_compliant
    expect(saveMock).toHaveBeenCalledWith({
      cat0_item0: 'non_compliant',
      cat0_item1: 'non_compliant',
    });
    expect((c as any).score()).toBe(88);
    expect((c as any).updatedAt()).toBe('2024-07-01T12:00:00Z');
    expect((c as any).saving()).toBe(false);
    expect(snack.open).toHaveBeenCalledWith('Évaluation sauvegardée', 'OK', { duration: 3000 });
  });

  it('erreur : coupe saving et affiche un snack erreur', () => {
    const c = makeWithCats(1);
    (c as any).saving = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          saveNis2Assessment: vi.fn().mockReturnValue(throwError(() => new Error('nope'))),
        };
    const snack = { open: vi.fn() };
    (c as any).snack = snack;
    c.save();
    expect((c as any).saving()).toBe(false);
    expect(snack.open).toHaveBeenCalledWith('Erreur lors de la sauvegarde', 'Fermer', {
      duration: 4000,
    });
  });
});

// ── exportPdf() ───────────────────────────────────────────────────────────────

describe('exportPdf()', () => {
  beforeEach(() => {
    (URL as any).createObjectURL = vi.fn().mockReturnValue('blob:fake');
    (URL as any).revokeObjectURL = vi.fn();
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: vi.fn(),
    } as any);
  });

  it('cas nominal : sauvegarde puis télécharge le blob', () => {
    const c = makeWithCats(1);
    (c as any).exporting = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          saveNis2Assessment: vi.fn().mockReturnValue(of({ score: 10, updated_at: 'd' })),
          downloadNis2PdfBlob: vi.fn().mockReturnValue(of(new Blob(['x']))),
        };
    (c as any).snack = { open: vi.fn() };
    c.exportPdf();
    expect((c as any).score()).toBe(10);
    expect((c as any).updatedAt()).toBe('d');
    expect((c as any).exporting()).toBe(false);
    expect((URL as any).createObjectURL).toHaveBeenCalled();
  });

  it('erreur de sauvegarde : coupe exporting et snack', () => {
    const c = makeWithCats(1);
    (c as any).exporting = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          saveNis2Assessment: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
          downloadNis2PdfBlob: vi.fn(),
        };
    const snack = { open: vi.fn() };
    (c as any).snack = snack;
    c.exportPdf();
    expect((c as any).exporting()).toBe(false);
    expect(snack.open).toHaveBeenCalledWith('Erreur lors de la sauvegarde avant export', 'Fermer', {
      duration: 4000,
    });
  });

  it('erreur de téléchargement : coupe exporting et snack export PDF', () => {
    const c = makeWithCats(1);
    (c as any).exporting = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          saveNis2Assessment: vi.fn().mockReturnValue(of({ score: 10, updated_at: 'd' })),
          downloadNis2PdfBlob: vi.fn().mockReturnValue(throwError(() => new Error('dl'))),
        };
    const snack = { open: vi.fn() };
    (c as any).snack = snack;
    c.exportPdf();
    expect((c as any).exporting()).toBe(false);
    expect(snack.open).toHaveBeenCalledWith("Erreur lors de l'export PDF", 'Fermer', {
      duration: 4000,
    });
  });

  it('403 : message « réservé aux plans payants » + action vers la grille tarifaire', () => {
    const c = makeWithCats(1);
    (c as any).exporting = signal(false);
    (c as any).canExport = signal(true);
    const actionRef = { onAction: vi.fn().mockReturnValue(of(void 0)) };
    const snack = { open: vi.fn().mockReturnValue(actionRef) };
    (c as any).snack = snack;
    (c as any).router = { navigate: vi.fn() };
    (c as any).complianceApi = {
      saveNis2Assessment: vi.fn().mockReturnValue(of({ score: 10, updated_at: 'd' })),
      downloadNis2PdfBlob: vi.fn().mockReturnValue(throwError(() => ({ status: 403 }))),
    };
    c.exportPdf();
    expect((c as any).exporting()).toBe(false);
    expect((c as any).canExport()).toBe(false);
    expect(snack.open).toHaveBeenCalledWith(
      "L'export PDF est réservé aux plans payants (dès Starter).",
      'Voir les offres',
      { duration: 7000 }
    );
    expect((c as any).router.navigate).toHaveBeenCalledWith(['/dashboard'], {
      queryParams: { upgrade: 'true' },
    });
  });
});

// ── exportAuditorPdf() ────────────────────────────────────────────────────────

describe('exportAuditorPdf()', () => {
  beforeEach(() => {
    (URL as any).createObjectURL = vi.fn().mockReturnValue('blob:fake');
    (URL as any).revokeObjectURL = vi.fn();
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: vi.fn(),
    } as any);
  });

  it('cas nominal : sauvegarde puis télécharge le document officiel', () => {
    const c = makeWithCats(1);
    (c as any).exportingAuditor = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          saveNis2Assessment: vi.fn().mockReturnValue(of({ score: 20, updated_at: 'e' })),
          downloadNis2AuditorPdfBlob: vi.fn().mockReturnValue(of(new Blob(['y']))),
        };
    (c as any).snack = { open: vi.fn() };
    c.exportAuditorPdf();
    expect((c as any).score()).toBe(20);
    expect((c as any).updatedAt()).toBe('e');
    expect((c as any).exportingAuditor()).toBe(false);
    expect((URL as any).createObjectURL).toHaveBeenCalled();
  });

  it('erreur de sauvegarde : coupe exportingAuditor et snack', () => {
    const c = makeWithCats(1);
    (c as any).exportingAuditor = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          saveNis2Assessment: vi.fn().mockReturnValue(throwError(() => new Error('x'))),
          downloadNis2AuditorPdfBlob: vi.fn(),
        };
    const snack = { open: vi.fn() };
    (c as any).snack = snack;
    c.exportAuditorPdf();
    expect((c as any).exportingAuditor()).toBe(false);
    expect(snack.open).toHaveBeenCalledWith('Erreur lors de la sauvegarde avant export', 'Fermer', {
      duration: 4000,
    });
  });

  it('erreur de téléchargement : coupe exportingAuditor et snack document officiel', () => {
    const c = makeWithCats(1);
    (c as any).exportingAuditor = signal(false);
    (c as any).cyberscan =
      (c as any).complianceApi =
      (c as any).publicScanApi =
      (c as any).notifApi =
      (c as any).codeScanApi =
      (c as any).urlScanApi =
      (c as any).scanApi =
      (c as any).siteApi =
        {
          saveNis2Assessment: vi.fn().mockReturnValue(of({ score: 20, updated_at: 'e' })),
          downloadNis2AuditorPdfBlob: vi.fn().mockReturnValue(throwError(() => new Error('dl'))),
        };
    const snack = { open: vi.fn() };
    (c as any).snack = snack;
    c.exportAuditorPdf();
    expect((c as any).exportingAuditor()).toBe(false);
    expect(snack.open).toHaveBeenCalledWith(
      "Erreur lors de l'export du document officiel",
      'Fermer',
      { duration: 4000 }
    );
  });
});

// ── Remédiation et preuve (fusion des deux produits NIS2, 2026-07-30) ─────────
//
// Ces deux méthodes décident si un prospect voit une sollicitation commerciale
// sur son diagnostic. Le cas « item non renseigné » est le piège : getStatus()
// retourne 'non_compliant' par défaut, et s'en servir afficherait six produits
// sur une évaluation vierge. C'est exactement l'erreur qu'il a fallu corriger
// côté PDF — d'où ces tests.

describe('aUnEcartDeclare()', () => {
  it('faux sur un item jamais renseigné', () => {
    const c = make();
    (c as any).items = signal({});
    expect(c.aUnEcartDeclare('awareness')).toBe(false);
  });

  it('vrai sur un écart déclaré non conforme', () => {
    const c = make();
    (c as any).items = signal({ awareness: 'non_compliant' });
    expect(c.aUnEcartDeclare('awareness')).toBe(true);
  });

  it('vrai sur un écart déclaré partiel', () => {
    const c = make();
    (c as any).items = signal({ awareness: 'partial' });
    expect(c.aUnEcartDeclare('awareness')).toBe(true);
  });

  it('faux sur un item déclaré conforme', () => {
    const c = make();
    (c as any).items = signal({ awareness: 'compliant' });
    expect(c.aUnEcartDeclare('awareness')).toBe(false);
  });

  it('faux sur un item déclaré non applicable', () => {
    const c = make();
    (c as any).items = signal({ awareness: 'na' });
    expect(c.aUnEcartDeclare('awareness')).toBe(false);
  });

  it('ne confond pas deux items différents', () => {
    const c = make();
    (c as any).items = signal({ awareness: 'non_compliant' });
    expect(c.aUnEcartDeclare('phishing_sim')).toBe(false);
  });
});

describe('preuve()', () => {
  it('null quand la plateforme ne mesure rien pour cet item', () => {
    const c = make();
    (c as any).preuves = signal({});
    expect(c.preuve('awareness')).toBeNull();
  });

  it('retourne la mesure quand elle existe', () => {
    const c = make();
    const mesure = { organisations: 1, apprenants: 15, termines: 12, pct: 80 };
    (c as any).preuves = signal({ awareness: mesure });
    expect(c.preuve('awareness')).toEqual(mesure);
  });

  it('null pour un item sans mesure, même si un autre en a une', () => {
    const c = make();
    (c as any).preuves = signal({
      awareness: { organisations: 1, apprenants: 5, termines: 5, pct: 100 },
    });
    expect(c.preuve('phishing_sim')).toBeNull();
  });

  it('la mesure est indépendante de la déclaration', () => {
    // Point clé : 100 % de salariés formés ne change PAS le statut déclaré.
    // L'utilisateur déclare, la plateforme mesure.
    const c = make();
    (c as any).items = signal({});
    (c as any).preuves = signal({
      awareness: { organisations: 1, apprenants: 10, termines: 10, pct: 100 },
    });
    expect(c.preuve('awareness')?.pct).toBe(100);
    expect(c.getStatus('awareness')).toBe('non_compliant');
    expect(c.aUnEcartDeclare('awareness')).toBe(false);
  });
});

// ── Template : ce que la page affiche réellement ─────────────────────────────
//
// Aucun spec du projet ne fait de rendu de template (pas de TestBed). On vérifie
// donc la SOURCE, comme le fait déjà landing.component.spec.ts.
//
// LIMITE ASSUMÉE : ces tests attrapent une suppression de bloc ou une condition
// changée, pas une erreur de rendu. Un vrai test de rendu exigerait d'introduire
// TestBed, ce que le projet ne fait nulle part.

describe('Template — blocs de remédiation et de preuve', () => {
  const tpl = readFileSync(resolve(__dirname, './nis2.component.html'), 'utf-8');

  it('la remédiation est conditionnée à un écart DÉCLARÉ', () => {
    // Si quelqu'un remplace aUnEcartDeclare() par getStatus(), six produits
    // s'afficheraient sur une évaluation vierge — le défaut corrigé côté PDF.
    expect(tpl).toContain('@if (item.remediation && aUnEcartDeclare(item.id))');
  });

  it('la remédiation ne s’affiche jamais sans produit associé', () => {
    // `item.remediation &&` doit précéder la condition d'écart : un item sans
    // produit ne doit rien afficher, même en écart.
    const bloc = tpl.slice(tpl.indexOf('item.remediation'));
    expect(bloc.indexOf('item.remediation')).toBeLessThan(bloc.indexOf('aUnEcartDeclare'));
  });

  it('la remédiation pointe vers la route fournie par le référentiel', () => {
    expect(tpl).toContain('[routerLink]="item.remediation.route"');
    expect(tpl).toContain('item.remediation.produit');
  });

  it('la preuve s’affiche dès qu’elle existe, indépendamment du statut déclaré', () => {
    // Volontairement PAS conditionnée à aUnEcartDeclare : la mesure est un fait,
    // elle s'affiche que l'utilisateur se déclare conforme ou non.
    expect(tpl).toContain('@if (preuve(item.id); as p)');
  });

  it('la preuve affiche le rapport terminés/apprenants et le pourcentage', () => {
    expect(tpl).toContain('p.termines');
    expect(tpl).toContain('p.apprenants');
    expect(tpl).toContain('p.pct');
  });

  it('la preuve est présentée comme une mesure, pas comme une réponse', () => {
    // Le libellé ne doit pas suggérer que l'item est rempli.
    expect(tpl).toContain('Mesuré sur votre plateforme');
  });
});
