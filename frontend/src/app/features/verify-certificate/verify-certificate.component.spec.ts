import { describe, it, expect } from 'vitest';
import { signal } from '@angular/core';
import { VerifyCertificateComponent } from './verify-certificate.component';
import type { CertificateVerification } from '../cyberscan/services/awareness.service';

function make(): VerifyCertificateComponent {
  const comp = Object.create(VerifyCertificateComponent.prototype) as VerifyCertificateComponent;
  (comp as any).cert = signal<CertificateVerification | null>(null);
  (comp as any).loading = signal(true);
  return comp;
}

describe('VerifyCertificateComponent — états des signaux', () => {
  it('loading est true initialement', () => {
    expect(make().loading()).toBe(true);
  });

  it('cert est null initialement', () => {
    expect(make().cert()).toBeNull();
  });

  it('loading peut passer à false', () => {
    const comp = make();
    (comp as any).loading.set(false);
    expect(comp.loading()).toBe(false);
  });

  it('cert peut recevoir des données valides', () => {
    const comp = make();
    const fakeCert: CertificateVerification = {
      valid: true,
      public_id: 'CERT-123',
      learner_name: 'Alice',
      program_title: 'NIS2 Fondamentaux',
      issued_at: '2026-01-01T00:00:00Z',
      expires_at: null,
      verification_count: 1,
    };
    (comp as any).cert.set(fakeCert);
    expect(comp.cert()?.public_id).toBe('CERT-123');
    expect(comp.cert()?.learner_name).toBe('Alice');
  });
});
