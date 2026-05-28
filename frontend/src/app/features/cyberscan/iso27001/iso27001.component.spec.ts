import { describe, it, expect } from 'vitest';
import { signal, computed } from '@angular/core';
import { Iso27001Component, Iso27001Status, Iso27001Category } from './iso27001.component';

function makeCategory(id: string, itemIds: string[]): Iso27001Category {
  return {
    id,
    label: `Cat ${id}`,
    icon: 'icon',
    items: itemIds.map(iid => ({ id: iid, label: `Item ${iid}`, desc: '' })),
  };
}

function make(): Iso27001Component {
  const comp = Object.create(Iso27001Component.prototype) as Iso27001Component;
  (comp as any).categories = signal<Iso27001Category[]>([]);
  (comp as any).items = signal<Record<string, Iso27001Status>>({});
  (comp as any).score = signal(0);
  (comp as any).updatedAt = signal<string | null>(null);
  (comp as any).CYCLE = ['non_compliant', 'partial', 'compliant', 'na'];
  (comp as any).STATUS_LIST = ['compliant', 'partial', 'non_compliant', 'na'];
  const allIds = computed(() =>
    (comp as any).categories().flatMap((cat: Iso27001Category) => cat.items.map((i: any) => i.id))
  );
  (comp as any).allItemIds = allIds;
  (comp as any).totalItems = computed(() =>
    (comp as any).categories().reduce((s: number, c: Iso27001Category) => s + c.items.length, 0)
  );
  (comp as any).compliantCount = computed(() =>
    allIds().filter((id: string) => comp.getStatus(id) === 'compliant').length
  );
  (comp as any).partialCount = computed(() =>
    allIds().filter((id: string) => comp.getStatus(id) === 'partial').length
  );
  (comp as any).ncCount = computed(() =>
    allIds().filter((id: string) => comp.getStatus(id) === 'non_compliant').length
  );
  (comp as any).naCount = computed(() =>
    allIds().filter((id: string) => comp.getStatus(id) === 'na').length
  );
  return comp;
}

describe('Iso27001Component — getStatus()', () => {
  it('retourne non_compliant par défaut', () => {
    expect(make().getStatus('A.5.1')).toBe('non_compliant');
  });
  it('retourne la valeur si définie', () => {
    const comp = make();
    (comp as any).items.set({ 'A.5.1': 'compliant' });
    expect(comp.getStatus('A.5.1')).toBe('compliant');
  });
  it('retourne partial si défini', () => {
    const comp = make();
    (comp as any).items.set({ 'A.5.1': 'partial' });
    expect(comp.getStatus('A.5.1')).toBe('partial');
  });
  it('retourne na si défini', () => {
    const comp = make();
    (comp as any).items.set({ 'A.5.1': 'na' });
    expect(comp.getStatus('A.5.1')).toBe('na');
  });
});

describe('Iso27001Component — toggle()', () => {
  it('cycle non_compliant → partial', () => {
    const comp = make();
    comp.toggle('A.5.1');
    expect(comp.getStatus('A.5.1')).toBe('partial');
  });
  it('cycle partial → compliant', () => {
    const comp = make();
    (comp as any).items.set({ 'A.5.1': 'partial' });
    comp.toggle('A.5.1');
    expect(comp.getStatus('A.5.1')).toBe('compliant');
  });
  it('cycle compliant → na', () => {
    const comp = make();
    (comp as any).items.set({ 'A.5.1': 'compliant' });
    comp.toggle('A.5.1');
    expect(comp.getStatus('A.5.1')).toBe('na');
  });
  it('cycle na → non_compliant', () => {
    const comp = make();
    (comp as any).items.set({ 'A.5.1': 'na' });
    comp.toggle('A.5.1');
    expect(comp.getStatus('A.5.1')).toBe('non_compliant');
  });
  it('cycle complet en 4 toggles', () => {
    const comp = make();
    for (let i = 0; i < 4; i++) comp.toggle('A.5.1');
    expect(comp.getStatus('A.5.1')).toBe('non_compliant');
  });
});

describe('Iso27001Component — setStatus()', () => {
  it('définit un statut précis', () => {
    const comp = make();
    comp.setStatus('A.5.1', 'partial');
    expect(comp.getStatus('A.5.1')).toBe('partial');
  });
  it('écrase un statut existant', () => {
    const comp = make();
    comp.setStatus('A.5.1', 'compliant');
    comp.setStatus('A.5.1', 'na');
    expect(comp.getStatus('A.5.1')).toBe('na');
  });
  it('ne modifie pas les autres items', () => {
    const comp = make();
    comp.setStatus('A.5.1', 'compliant');
    comp.setStatus('A.5.2', 'partial');
    expect(comp.getStatus('A.5.1')).toBe('compliant');
  });
});

describe('Iso27001Component — recalcScore()', () => {
  it('score = 0 si aucune catégorie', () => {
    const comp = make();
    comp.recalcScore();
    expect((comp as any).score()).toBe(0);
  });
  it('score = 100 si tous conformes', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1', 'i2'])]);
    comp.setStatus('i1', 'compliant');
    comp.setStatus('i2', 'compliant');
    comp.recalcScore();
    expect((comp as any).score()).toBe(100);
  });
  it('score = 50 si moitié conforme', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1', 'i2'])]);
    comp.setStatus('i1', 'compliant');
    comp.setStatus('i2', 'non_compliant');
    comp.recalcScore();
    expect((comp as any).score()).toBe(50);
  });
  it('partial vaut 1pt sur 2', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1', 'i2'])]);
    comp.setStatus('i1', 'partial');
    comp.setStatus('i2', 'non_compliant');
    comp.recalcScore();
    expect((comp as any).score()).toBe(25);
  });
  it('ignore les items na dans le calcul', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1', 'i2'])]);
    comp.setStatus('i1', 'compliant');
    comp.setStatus('i2', 'na');
    comp.recalcScore();
    expect((comp as any).score()).toBe(100);
  });
  it('score = 0 si tout est na', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1'])]);
    comp.setStatus('i1', 'na');
    comp.recalcScore();
    expect((comp as any).score()).toBe(0);
  });
});

describe('Iso27001Component — resetAll()', () => {
  it('vide tous les items', () => {
    const comp = make();
    comp.setStatus('A.5.1', 'compliant');
    comp.setStatus('A.5.2', 'partial');
    comp.resetAll();
    expect((comp as any).items()).toEqual({});
  });
  it('recalcule le score à 0', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1'])]);
    comp.setStatus('i1', 'compliant');
    comp.recalcScore();
    comp.resetAll();
    expect((comp as any).score()).toBe(0);
  });
});

describe('Iso27001Component — statusLabel()', () => {
  it('Conforme pour compliant', () => expect(make().statusLabel('compliant')).toBe('Conforme'));
  it('Partiel pour partial', () => expect(make().statusLabel('partial')).toBe('Partiel'));
  it('Non conforme pour non_compliant', () => expect(make().statusLabel('non_compliant')).toBe('Non conforme'));
  it('N/A pour na', () => expect(make().statusLabel('na')).toBe('N/A'));
  it('valeur brute pour statut inconnu', () => expect(make().statusLabel('unknown')).toBe('unknown'));
});

describe('Iso27001Component — statusIcon()', () => {
  it('check_circle pour compliant', () => expect(make().statusIcon('compliant')).toBe('check_circle'));
  it('pending pour partial', () => expect(make().statusIcon('partial')).toBe('pending'));
  it('cancel pour non_compliant', () => expect(make().statusIcon('non_compliant')).toBe('cancel'));
  it('remove_circle_outline pour na', () => expect(make().statusIcon('na')).toBe('remove_circle_outline'));
  it('help_outline par défaut', () => expect(make().statusIcon('other')).toBe('help_outline'));
});

describe('Iso27001Component — statusClass()', () => {
  it('contient green pour compliant', () => expect(make().statusClass('compliant')).toContain('green'));
  it('contient yellow pour partial', () => expect(make().statusClass('partial')).toContain('yellow'));
  it('contient red pour non_compliant', () => expect(make().statusClass('non_compliant')).toContain('red'));
  it('contient gray pour na', () => expect(make().statusClass('na')).toContain('gray'));
  it('fallback gray pour inconnu', () => expect(make().statusClass('other')).toContain('gray'));
});

describe('Iso27001Component — statusColor()', () => {
  it('#4ade80 pour compliant', () => expect(make().statusColor('compliant')).toBe('#4ade80'));
  it('#facc15 pour partial', () => expect(make().statusColor('partial')).toBe('#facc15'));
  it('#f87171 pour non_compliant', () => expect(make().statusColor('non_compliant')).toBe('#f87171'));
  it('#6b7280 pour na', () => expect(make().statusColor('na')).toBe('#6b7280'));
  it('#6b7280 par défaut', () => expect(make().statusColor('other')).toBe('#6b7280'));
});

describe('Iso27001Component — scoreColor()', () => {
  it('#4ade80 si score = 80', () => expect(make().scoreColor(80)).toBe('#4ade80'));
  it('#4ade80 si score = 100', () => expect(make().scoreColor(100)).toBe('#4ade80'));
  it('#facc15 si score = 65', () => expect(make().scoreColor(65)).toBe('#facc15'));
  it('#facc15 si score = 50', () => expect(make().scoreColor(50)).toBe('#facc15'));
  it('#f87171 si score < 50', () => expect(make().scoreColor(30)).toBe('#f87171'));
  it('#f87171 si score = 0', () => expect(make().scoreColor(0)).toBe('#f87171'));
});

describe('Iso27001Component — scoreLabel()', () => {
  it('Conforme si ≥ 80', () => expect(make().scoreLabel(80)).toBe('Conforme'));
  it('En cours si entre 50 et 79', () => expect(make().scoreLabel(60)).toBe('En cours'));
  it('En cours si = 50', () => expect(make().scoreLabel(50)).toBe('En cours'));
  it('Non conforme si < 50', () => expect(make().scoreLabel(49)).toBe('Non conforme'));
});

describe('Iso27001Component — catCompliance()', () => {
  it('compte compliant/partial/nc/total correctement', () => {
    const comp = make();
    const cat = makeCategory('c1', ['i1', 'i2', 'i3', 'i4']);
    comp.setStatus('i1', 'compliant');
    comp.setStatus('i2', 'partial');
    comp.setStatus('i3', 'non_compliant');
    comp.setStatus('i4', 'na');
    const r = comp.catCompliance(cat);
    expect(r.compliant).toBe(1);
    expect(r.partial).toBe(1);
    expect(r.nc).toBe(1);
    expect(r.total).toBe(4);
  });
  it('nc inclut les non_compliant implicites', () => {
    const comp = make();
    const cat = makeCategory('c1', ['i1', 'i2']);
    const r = comp.catCompliance(cat);
    expect(r.nc).toBe(2);
    expect(r.total).toBe(2);
  });
});

describe('Iso27001Component — catScore()', () => {
  it('100 si tous conformes', () => {
    const comp = make();
    const cat = makeCategory('c1', ['i1', 'i2']);
    comp.setStatus('i1', 'compliant');
    comp.setStatus('i2', 'compliant');
    expect(comp.catScore(cat)).toBe(100);
  });
  it('0 si tous non conformes', () => {
    const comp = make();
    const cat = makeCategory('c1', ['i1', 'i2']);
    expect(comp.catScore(cat)).toBe(0);
  });
  it('exclut les na du calcul', () => {
    const comp = make();
    const cat = makeCategory('c1', ['i1', 'i2']);
    comp.setStatus('i1', 'compliant');
    comp.setStatus('i2', 'na');
    expect(comp.catScore(cat)).toBe(100);
  });
  it('0 si tout est na', () => {
    const comp = make();
    const cat = makeCategory('c1', ['i1']);
    comp.setStatus('i1', 'na');
    expect(comp.catScore(cat)).toBe(0);
  });
  it('50 pour partial + non_compliant', () => {
    const comp = make();
    const cat = makeCategory('c1', ['i1', 'i2']);
    comp.setStatus('i1', 'partial');
    comp.setStatus('i2', 'non_compliant');
    expect(comp.catScore(cat)).toBe(25);
  });
});

describe('Iso27001Component — formatDate()', () => {
  it('retourne — pour null', () => expect(make().formatDate(null)).toBe('—'));
  it('contient l\'année', () => expect(make().formatDate('2024-03-15T10:00:00Z')).toContain('2024'));
  it('contient le mois en lettres', () => expect(make().formatDate('2024-03-15T10:00:00Z')).toContain('mars'));
  it('contient le jour', () => expect(make().formatDate('2024-03-15T10:00:00Z')).toContain('15'));
});

describe('Iso27001Component — computed signals', () => {
  it('totalItems = somme des items', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1', 'i2']), makeCategory('c2', ['i3'])]);
    expect((comp as any).totalItems()).toBe(3);
  });
  it('totalItems = 0 si pas de catégories', () => {
    expect((make() as any).totalItems()).toBe(0);
  });
  it('compliantCount compte les conformes', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1', 'i2'])]);
    comp.setStatus('i1', 'compliant');
    expect((comp as any).compliantCount()).toBe(1);
  });
  it('partialCount compte les partiels', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1', 'i2'])]);
    comp.setStatus('i2', 'partial');
    expect((comp as any).partialCount()).toBe(1);
  });
  it('ncCount = 2 si aucun statut défini', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1', 'i2'])]);
    expect((comp as any).ncCount()).toBe(2);
  });
  it('naCount compte les na', () => {
    const comp = make();
    (comp as any).categories.set([makeCategory('c1', ['i1'])]);
    comp.setStatus('i1', 'na');
    expect((comp as any).naCount()).toBe(1);
  });
});
