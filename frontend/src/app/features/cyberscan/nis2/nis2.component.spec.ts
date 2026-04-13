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

import { describe, it, expect, beforeEach } from 'vitest';
import { signal, computed } from '@angular/core';
import { Nis2Component, Nis2Category, Nis2Status } from './nis2.component';

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Crée un composant avec ses signals initialisés, sans Angular DI. */
function make(): Nis2Component {
  const c = Object.create(Nis2Component.prototype) as Nis2Component;

  // Signals d'état
  (c as any).loading    = signal(false);
  (c as any).saving     = signal(false);
  (c as any).exporting  = signal(false);
  (c as any).score      = signal(0);
  (c as any).updatedAt  = signal<string | null>(null);

  // Données
  (c as any).categories = signal<Nis2Category[]>([]);
  (c as any).items      = signal<Record<string, Nis2Status>>({});

  // Constantes
  (c as any).CYCLE       = ['non_compliant', 'partial', 'compliant', 'na'];
  (c as any).STATUS_LIST = ['compliant', 'partial', 'non_compliant', 'na'];

  // Computed signals (reproduit la logique du composant)
  (c as any).allItemIds = computed(() =>
    (c as any).categories().flatMap((cat: Nis2Category) => cat.items.map(i => i.id))
  );
  (c as any).totalItems = computed(() =>
    (c as any).categories().reduce((s: number, cat: Nis2Category) => s + cat.items.length, 0)
  );
  (c as any).compliantCount = computed(() =>
    (c as any).allItemIds().filter((id: string) => c.getStatus(id) === 'compliant').length
  );
  (c as any).partialCount = computed(() =>
    (c as any).allItemIds().filter((id: string) => c.getStatus(id) === 'partial').length
  );
  (c as any).ncCount = computed(() =>
    (c as any).allItemIds().filter((id: string) => c.getStatus(id) === 'non_compliant').length
  );
  (c as any).naCount = computed(() =>
    (c as any).allItemIds().filter((id: string) => c.getStatus(id) === 'na').length
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
      id:    `${id}_item${i}`,
      label: `Item ${i}`,
      desc:  `Desc ${i}`,
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
  it('compliant → Conforme',        () => expect(c.statusLabel('compliant')).toBe('Conforme'));
  it('partial → Partiel',           () => expect(c.statusLabel('partial')).toBe('Partiel'));
  it('non_compliant → Non conforme',() => expect(c.statusLabel('non_compliant')).toBe('Non conforme'));
  it('na → N/A',                    () => expect(c.statusLabel('na')).toBe('N/A'));
  it('inconnu → valeur brute',      () => expect(c.statusLabel('foo')).toBe('foo'));
});


// ── statusIcon() ──────────────────────────────────────────────────────────────

describe('statusIcon()', () => {
  const c = make();
  it('compliant → check_circle',           () => expect(c.statusIcon('compliant')).toBe('check_circle'));
  it('partial → pending',                  () => expect(c.statusIcon('partial')).toBe('pending'));
  it('non_compliant → cancel',             () => expect(c.statusIcon('non_compliant')).toBe('cancel'));
  it('na → remove_circle_outline',         () => expect(c.statusIcon('na')).toBe('remove_circle_outline'));
  it('inconnu → help_outline',             () => expect(c.statusIcon('?')).toBe('help_outline'));
});


// ── statusClass() ─────────────────────────────────────────────────────────────

describe('statusClass()', () => {
  const c = make();
  it('compliant contient green',     () => expect(c.statusClass('compliant')).toContain('green'));
  it('partial contient yellow',      () => expect(c.statusClass('partial')).toContain('yellow'));
  it('non_compliant contient red',   () => expect(c.statusClass('non_compliant')).toContain('red'));
  it('na contient gray',             () => expect(c.statusClass('na')).toContain('gray'));
  it('inconnu → fallback gray',      () => expect(c.statusClass('?')).toContain('gray'));
});


// ── statusColor() ─────────────────────────────────────────────────────────────

describe('statusColor()', () => {
  const c = make();
  it('compliant → #4ade80',      () => expect(c.statusColor('compliant')).toBe('#4ade80'));
  it('partial → #facc15',        () => expect(c.statusColor('partial')).toBe('#facc15'));
  it('non_compliant → #f87171',  () => expect(c.statusColor('non_compliant')).toBe('#f87171'));
  it('na → #6b7280',             () => expect(c.statusColor('na')).toBe('#6b7280'));
  it('inconnu → #6b7280',        () => expect(c.statusColor('?')).toBe('#6b7280'));
});


// ── scoreColor() ──────────────────────────────────────────────────────────────

describe('scoreColor()', () => {
  const c = make();
  it('>= 80 → vert',   () => expect(c.scoreColor(80)).toBe('#4ade80'));
  it('100 → vert',     () => expect(c.scoreColor(100)).toBe('#4ade80'));
  it('50 → jaune',     () => expect(c.scoreColor(50)).toBe('#facc15'));
  it('79 → jaune',     () => expect(c.scoreColor(79)).toBe('#facc15'));
  it('49 → rouge',     () => expect(c.scoreColor(49)).toBe('#f87171'));
  it('0 → rouge',      () => expect(c.scoreColor(0)).toBe('#f87171'));
});


// ── scoreLabel() ──────────────────────────────────────────────────────────────

describe('scoreLabel()', () => {
  const c = make();
  it('>= 80 → Conforme',       () => expect(c.scoreLabel(80)).toBe('Conforme'));
  it('50-79 → En cours',       () => expect(c.scoreLabel(50)).toBe('En cours'));
  it('79 → En cours',          () => expect(c.scoreLabel(79)).toBe('En cours'));
  it('< 50 → Non conforme',    () => expect(c.scoreLabel(49)).toBe('Non conforme'));
  it('0 → Non conforme',       () => expect(c.scoreLabel(0)).toBe('Non conforme'));
});


// ── formatDate() ──────────────────────────────────────────────────────────────

describe('formatDate()', () => {
  const c = make();
  it('null → "—"',             () => expect(c.formatDate(null)).toBe('—'));
  it('ISO → contient l\'année',() => expect(c.formatDate('2024-06-15T10:00:00Z')).toContain('2024'));
  it('retourne une string',    () => expect(typeof c.formatDate('2025-01-01T00:00:00Z')).toBe('string'));
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

  it('toggle n\'affecte pas les autres items', () => {
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

  it('n\'affecte pas les autres items', () => {
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
    const c = makeWithCats(2);         // 2 items : cat0_item0, cat0_item1
    const [id0, id1] = (c as any).allItemIds();
    (c as any).items.set({ [id0]: 'compliant', [id1]: 'na' });
    c.recalcScore();
    expect((c as any).score()).toBe(100);
  });

  it('items non renseignés comptent comme non_compliant', () => {
    const c = makeWithCats(4);         // 4 items
    const [id0] = (c as any).allItemIds();
    (c as any).items.set({ [id0]: 'compliant' });  // 3 autres non renseignés
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
    const c = makeWithCats(4);         // 4 items
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
    expect((c as any).ncCount()).toBe(1);  // le 5ème item, non renseigné
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
    const sum = (c as any).compliantCount()
              + (c as any).partialCount()
              + (c as any).ncCount()
              + (c as any).naCount();
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
    expect(r.nc).toBe(3);   // défaut non_compliant
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
      z_item0: 'na', z_item1: 'na', z_item2: 'na',
    });
    expect(c.catScore(cat)).toBe(0);
  });

  it('retourne 100 si tous compliant', () => {
    const c = make();
    const cat = makeCat('a', 3);
    (c as any).items.set({
      a_item0: 'compliant', a_item1: 'compliant', a_item2: 'compliant',
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
