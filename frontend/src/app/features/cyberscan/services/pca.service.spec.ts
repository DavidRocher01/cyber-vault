import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of, throwError } from 'rxjs';
import { PcaService, PcaPayload } from './pca.service';

const URL = '/api/v1/pca/generate';

/**
 * PcaService uses Angular's inject() field initializer.
 * We bypass DI by creating an instance via Object.create and manually
 * assigning the http dependency — same pattern used across the other
 * cyberscan service specs (no TestBed env is initialised in this project).
 */
function makeService(httpOverrides: Partial<{ post: any }> = {}) {
  const http = {
    post: vi.fn().mockReturnValue(of(new Blob())),
    ...httpOverrides,
  };
  const service = Object.create(PcaService.prototype) as PcaService;
  (service as any).http = http;
  return { service, http };
}

function makePayload(): PcaPayload {
  return {
    company: {
      name: 'Acme SARL',
      sector: 'Industrie',
      contact: 'Jean Dupont',
      email: 'contact@acme.fr',
      phone: '+33123456789',
    },
    critical_systems: [
      {
        name: 'ERP',
        description: 'Système de gestion',
        rto_hours: 4,
        rpo_hours: 1,
        responsible: 'DSI',
      },
    ],
    response_team: [
      {
        name: 'Alice Martin',
        role: 'RSSI',
        phone: '+33600000000',
        email: 'alice@acme.fr',
      },
    ],
    communication_plan: 'Escalade interne puis externe.',
  };
}

describe('PcaService — generate()', () => {
  let service: PcaService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  it('appelle POST /api/v1/pca/generate', () => {
    service.generate(makePayload()).subscribe();
    expect(http.post).toHaveBeenCalledWith(URL, expect.anything(), expect.anything());
    expect(http.post).toHaveBeenCalledTimes(1);
  });

  it('transmet le payload complet en body', () => {
    const payload = makePayload();
    service.generate(payload).subscribe();
    const [, body] = http.post.mock.calls[0];
    expect(body).toEqual(payload);
  });

  it('demande une réponse de type blob', () => {
    service.generate(makePayload()).subscribe();
    const [, , options] = http.post.mock.calls[0];
    expect(options).toEqual({ responseType: 'blob' });
  });

  it('retourne le Blob émis par le serveur', () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' });
    http.post.mockReturnValue(of(blob));
    let received: Blob | undefined;
    service.generate(makePayload()).subscribe(r => (received = r));
    expect(received).toBe(blob);
    expect(received!.type).toBe('application/pdf');
  });

  it('propage une erreur HTTP au subscriber', () => {
    http.post.mockReturnValue(throwError(() => ({ status: 500 })));
    let errorStatus: number | undefined;
    service.generate(makePayload()).subscribe({
      next: () => {
        throw new Error('ne doit pas réussir');
      },
      error: (err: { status: number }) => (errorStatus = err.status),
    });
    expect(errorStatus).toBe(500);
  });
});
