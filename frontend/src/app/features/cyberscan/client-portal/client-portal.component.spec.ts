import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { ClientPortalComponent } from './client-portal.component';
import { PortalAction } from '../services/client-portal.service';

// Helpers purs : testés sans DI (les méthodes vivent sur le prototype).
const c = Object.create(ClientPortalComponent.prototype) as ClientPortalComponent;

describe('ClientPortalComponent — libellés & helpers', () => {
  it('priorityLabel : connu + repli', () => {
    expect(c.priorityLabel('critical')).toBe('Critique');
    expect(c.priorityLabel('low')).toBe('Basse');
    expect(c.priorityLabel('inconnu')).toBe('inconnu');
  });

  it('priorityClass : classe adaptée + repli gris', () => {
    expect(c.priorityClass('high')).toContain('orange');
    expect(c.priorityClass('xxx')).toContain('gray');
  });

  it('actionStatusLabel / actionStatusClass', () => {
    expect(c.actionStatusLabel('done')).toBe('Terminée');
    expect(c.actionStatusLabel('open')).toBe('À faire');
    expect(c.actionStatusClass('done')).toContain('green');
    expect(c.actionStatusClass('xxx')).toBe('text-gray-400');
  });

  it('visitTypeLabel / visitStatus', () => {
    expect(c.visitTypeLabel('quarterly')).toBe('Comité trimestriel');
    expect(c.visitTypeLabel('xxx')).toBe('xxx');
    expect(c.visitStatusLabel('planned')).toBe('Planifiée');
    expect(c.visitStatusClass('done')).toContain('green');
  });

  it('docTypeLabel', () => {
    expect(c.docTypeLabel('rapport')).toBe('Rapport');
    expect(c.docTypeLabel('xxx')).toBe('xxx');
  });

  it('formulaLabel gère null', () => {
    expect(c.formulaLabel('premium')).toBe('Premium');
    expect(c.formulaLabel(null)).toBe('—');
  });

  it('formatDate gère null + date valide', () => {
    expect(c.formatDate(null)).toBe('—');
    expect(c.formatDate('2026-01-15')).toContain('2026');
  });

  it('isDone', () => {
    expect(c.isDone({ status: 'done' } as PortalAction)).toBe(true);
    expect(c.isDone({ status: 'open' } as PortalAction)).toBe(false);
  });
});

// ── Depot de document (etape 3) ───────────────────────────────────────────────
//
// L'analyse antivirus est asynchrone : un document apparait AVANT d'etre
// telechargeable. Sans etat affiche, cet ecart ressemble a une panne — et le
// bouton d'ouverture doit refuser d'ouvrir ce qui n'est pas repute sain.

describe('ClientPortalComponent — etat d analyse', () => {
  function c(): ClientPortalComponent {
    return Object.create(ClientPortalComponent.prototype) as ClientPortalComponent;
  }

  it('n affiche AUCUNE puce pour un fichier sain', () => {
    // Le cas normal ne doit rien signaler : une pastille verte sur chaque ligne
    // fatiguerait l'oeil sans rien apprendre.
    expect(c().analyseLibelle('sain')).toBeNull();
  });

  it('n affiche aucune puce pour un fichier anterieur au registre', () => {
    expect(c().analyseLibelle(null)).toBeNull();
  });

  it('nomme les trois etats qui demandent de l attention', () => {
    expect(c().analyseLibelle('en_analyse')).toContain('Vérification');
    expect(c().analyseLibelle('rejete')).toContain('Refusé');
    expect(c().analyseLibelle('indetermine')).toContain('Non vérifiable');
  });

  it('distingue non-verifiable de refuse par la couleur', () => {
    // `indetermine` n'est ni vert ni rouge : l'analyse n'a pas abouti, accuser
    // serait aussi faux que rassurer.
    const comp = c();
    expect(comp.analyseClasses('indetermine')).toContain('violet');
    expect(comp.analyseClasses('rejete')).toContain('red');
  });
});

describe('ClientPortalComponent — ce qui est ouvrable', () => {
  function c(): ClientPortalComponent {
    return Object.create(ClientPortalComponent.prototype) as ClientPortalComponent;
  }
  const doc = (statut: unknown, has_file = true) =>
    ({ id: 1, has_file, statut_analyse: statut }) as never;

  it('ouvre un fichier sain', () => {
    expect(c().ouvrable(doc('sain'))).toBe(true);
  });

  it('ouvre un fichier anterieur au registre', () => {
    expect(c().ouvrable(doc(null))).toBe(true);
  });

  it('REFUSE d ouvrir un fichier en analyse, rejete ou non verifiable', () => {
    const comp = c();
    expect(comp.ouvrable(doc('en_analyse'))).toBe(false);
    expect(comp.ouvrable(doc('rejete'))).toBe(false);
    expect(comp.ouvrable(doc('indetermine'))).toBe(false);
  });

  it('n ouvre rien sans fichier', () => {
    expect(c().ouvrable(doc('sain', false))).toBe(false);
  });
});

describe('ClientPortalComponent — quota et tailles', () => {
  function c(): ClientPortalComponent {
    const comp = Object.create(ClientPortalComponent.prototype) as ClientPortalComponent;
    (comp as never as { quota: unknown }).quota = signal(null);
    return comp;
  }

  it('formate les tailles de facon lisible', () => {
    const comp = c();
    expect(comp.formatOctets(512)).toBe('512 o');
    expect(comp.formatOctets(2048)).toBe('2 Ko');
    expect(comp.formatOctets(3 * 1024 * 1024)).toBe('3.0 Mo');
    expect(comp.formatOctets(500 * 1024 * 1024)).toBe('500 Mo');
  });

  it('rend 0 % sans quota charge, jamais NaN', () => {
    expect(c().quotaPourcent()).toBe(0);
  });

  it('plafonne a 100 % meme si le quota est depasse', () => {
    const comp = c();
    (comp as never as { quota: { set: (v: unknown) => void } }).quota.set({
      utilise_octets: 900,
      quota_octets: 500,
      taille_max_fichier_octets: 20,
    });
    expect(comp.quotaPourcent()).toBe(100);
  });
});
