import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { ComplianceApiService } from './compliance-api.service';

const API = '/api/v1';

/**
 * ComplianceApiService uses Angular's inject() field initializer.
 * We bypass DI by creating an instance via Object.create and manually
 * assigning the http dependency — same pattern used for constructor injection.
 */
function makeService(httpOverrides: Partial<{ get: any; post: any; put: any; delete: any }> = {}) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    put: vi.fn().mockReturnValue(of({})),
    delete: vi.fn().mockReturnValue(of(null)),
    ...httpOverrides,
  };
  const service = Object.create(ComplianceApiService.prototype) as ComplianceApiService;
  (service as any).http = http;
  // Reset in-memory caches so each test starts fresh
  (service as any)._plans$ = null;
  (service as any)._subscription$ = null;
  return { service, http };
}

describe('ComplianceApiService', () => {
  let service: ComplianceApiService;
  let http: any;

  beforeEach(() => {
    ({ service, http } = makeService());
  });

  // ── Plans ──────────────────────────────────────────────────────────────────

  // ── Sites ──────────────────────────────────────────────────────────────────

  // ── Scans ──────────────────────────────────────────────────────────────────

  // ── URL Scans ──────────────────────────────────────────────────────────────

  // ── Code Scans ─────────────────────────────────────────────────────────────

  // ── Notifications ──────────────────────────────────────────────────────────

  // ── NIS2 ──────────────────────────────────────────────────────────────────

  it('getNis2Assessment() envoie GET /api/v1/nis2/me', () => {
    http.get.mockReturnValue(of({ score: 0, items: {}, categories: [] }));
    service.getNis2Assessment().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/nis2/me`);
  });

  it('getNis2Assessment() retourne les données du serveur', () => {
    const data = { score: 75, items: { rssi: 'compliant' }, categories: [] };
    http.get.mockReturnValue(of(data));
    let result: any;
    service.getNis2Assessment().subscribe(r => (result = r));
    expect(result.score).toBe(75);
    expect(result.items.rssi).toBe('compliant');
  });

  it('saveNis2Assessment() envoie PUT /api/v1/nis2/me avec { items }', () => {
    const items = { rssi: 'compliant', policy: 'partial' };
    http.put.mockReturnValue(of({ score: 75, items }));
    service.saveNis2Assessment(items).subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/nis2/me`, { items });
  });

  it('saveNis2Assessment() retourne la réponse avec le score', () => {
    const items = { rssi: 'compliant' };
    http.put.mockReturnValue(of({ score: 100, items }));
    let result: any;
    service.saveNis2Assessment(items).subscribe(r => (result = r));
    expect(result.score).toBe(100);
  });

  it('saveNis2Assessment() envoie exactement un PUT', () => {
    http.put.mockReturnValue(of({}));
    service.saveNis2Assessment({}).subscribe();
    expect(http.put).toHaveBeenCalledTimes(1);
  });

  it('downloadNis2PdfBlob() envoie GET /api/v1/nis2/me/pdf avec responseType blob', () => {
    const blob = new Blob(['PDF'], { type: 'application/pdf' });
    http.get.mockReturnValue(of(blob));
    service.downloadNis2PdfBlob().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/nis2/me/pdf`, { responseType: 'blob' });
  });

  it('downloadNis2PdfBlob() retourne un Blob', () => {
    const blob = new Blob(['PDF'], { type: 'application/pdf' });
    http.get.mockReturnValue(of(blob));
    let result: any;
    service.downloadNis2PdfBlob().subscribe(r => (result = r));
    expect(result).toBe(blob);
  });
});

// ── Le sujet de l'évaluation (étape 5d) ──────────────────────────────────────
//
// Un seul composant sert deux sujets : mon auto-évaluation et le dossier qu'un
// consultant monte pour un client. C'est le service qui traduit le sujet en
// préfixe de route. Se tromper ici ferait lire, écrire ou déposer sur le mauvais
// dossier — sans aucune erreur visible.

describe('ComplianceApiService — sujet de l’évaluation', () => {
  const CLIENT = '/api/v1/rssi/clients/42/nis2';
  const MOI = `${API}/nis2/me`;

  it('sans sujet, vise mon auto-évaluation', () => {
    const { service, http } = makeService();
    service.getNis2Assessment().subscribe();
    expect(http.get).toHaveBeenCalledWith(MOI);
  });

  it('avec un clientId, vise le dossier de ce client', () => {
    const { service, http } = makeService();
    service.getNis2Assessment(42).subscribe();
    expect(http.get).toHaveBeenCalledWith(CLIENT);
  });

  it('null vaut « moi », pas « client 0 »', () => {
    const { service, http } = makeService();
    service.getNis2Assessment(null).subscribe();
    expect(http.get).toHaveBeenCalledWith(MOI);
  });

  it('la sauvegarde suit le sujet', () => {
    const { service, http } = makeService();
    service.saveNis2Assessment({ rssi: 'compliant' }, 42).subscribe();
    expect(http.put).toHaveBeenCalledWith(CLIENT, { items: { rssi: 'compliant' } });
  });

  it('le dépôt de pièce suit le sujet', () => {
    const { service, http } = makeService();
    service.deposerPiece('rssi', new File(['x'], 'p.pdf'), 42).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${CLIENT}/criteres/rssi/pieces`, expect.anything());
  });

  it("l'identifiant de critère est encodé dans l'URL", () => {
    const { service, http } = makeService();
    service.deposerPiece('a/b', new File(['x'], 'p.pdf')).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${MOI}/criteres/a%2Fb/pieces`, expect.anything());
  });

  it('le retrait et le téléchargement suivent le sujet', () => {
    const { service, http } = makeService();
    service.retirerPiece(9, 42).subscribe();
    service.lienPiece(9, 42).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${CLIENT}/pieces/9`);
    expect(http.get).toHaveBeenCalledWith(`${CLIENT}/pieces/9/download`);
  });

  it('le document auditeur suit le sujet', () => {
    const { service, http } = makeService();
    service.downloadNis2AuditorPdfBlob(42).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${CLIENT}/pdf/auditor`, { responseType: 'blob' });
  });
});
