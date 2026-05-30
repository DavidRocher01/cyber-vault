import { describe, it, expect, vi } from 'vitest';
import { of } from 'rxjs';
import { PhishingService } from './phishing.service';

const BASE = '/api/v1/phishing';

function makeService(httpOverrides: Partial<{ get: any; post: any; patch: any }> = {}) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    patch: vi.fn().mockReturnValue(of({})),
    ...httpOverrides,
  };
  const service = Object.create(PhishingService.prototype) as PhishingService;
  (service as any).http = http;
  (service as any).base = BASE;
  return { service, http };
}

describe('PhishingService — getPdfUrl()', () => {
  it("retourne l'URL correcte pour un id donné", () => {
    const { service } = makeService();
    expect(service.getPdfUrl(42)).toBe(`${BASE}/campaigns/42/pdf`);
  });
  it("fonctionne pour l'id 1", () => {
    const { service } = makeService();
    expect(service.getPdfUrl(1)).toContain('/campaigns/1/pdf');
  });
});

describe('PhishingService — getCampaigns()', () => {
  it('appelle GET /phishing/campaigns', () => {
    const { service, http } = makeService();
    service.getCampaigns().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${BASE}/campaigns`);
  });
});

describe('PhishingService — getCampaign()', () => {
  it('appelle GET /phishing/campaigns/:id', () => {
    const { service, http } = makeService();
    service.getCampaign(5).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${BASE}/campaigns/5`);
  });
});

describe('PhishingService — createCampaign()', () => {
  it('appelle POST /phishing/campaigns avec name et plan_tier', () => {
    const { service, http } = makeService();
    service.createCampaign('Test', 'standard').subscribe();
    expect(http.post).toHaveBeenCalledWith(`${BASE}/campaigns`, {
      name: 'Test',
      plan_tier: 'standard',
    });
  });
});

describe('PhishingService — updateCampaign()', () => {
  it('appelle PATCH /phishing/campaigns/:id avec le patch', () => {
    const { service, http } = makeService();
    service.updateCampaign(3, { name: 'Nouveau nom', cgu_accepted: true }).subscribe();
    expect(http.patch).toHaveBeenCalledWith(`${BASE}/campaigns/3`, {
      name: 'Nouveau nom',
      cgu_accepted: true,
    });
  });
  it('accepte un patch vide', () => {
    const { service, http } = makeService();
    service.updateCampaign(3, {}).subscribe();
    expect(http.patch).toHaveBeenCalledWith(`${BASE}/campaigns/3`, {});
  });
});

describe('PhishingService — launchCampaign()', () => {
  it('appelle POST /phishing/campaigns/:id/launch avec un body vide', () => {
    const { service, http } = makeService();
    service.launchCampaign(7).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${BASE}/campaigns/7/launch`, {});
  });
});

describe('PhishingService — getLookalikeDomains()', () => {
  it('appelle GET /phishing/lookalike-domains avec domain en param', () => {
    const { service, http } = makeService();
    service.getLookalikeDomains('acme.fr').subscribe();
    expect(http.get).toHaveBeenCalledWith(`${BASE}/lookalike-domains`, {
      params: { domain: 'acme.fr' },
    });
  });
});

describe('PhishingService — uploadTargets()', () => {
  it('appelle POST /phishing/campaigns/:id/targets avec un FormData', () => {
    const { service, http } = makeService();
    const file = new File(['a,b'], 'targets.csv', { type: 'text/csv' });
    service.uploadTargets(4, file).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${BASE}/campaigns/4/targets`, expect.any(FormData));
  });
});

describe('PhishingService — requestDomainVerify()', () => {
  it('appelle POST /phishing/domain-verify avec le domain', () => {
    const { service, http } = makeService();
    service.requestDomainVerify('acme.fr').subscribe();
    expect(http.post).toHaveBeenCalledWith(`${BASE}/domain-verify`, { domain: 'acme.fr' });
  });
});

describe('PhishingService — checkDomainVerify()', () => {
  it('appelle POST /phishing/domain-verify/check avec le domain', () => {
    const { service, http } = makeService();
    service.checkDomainVerify('acme.fr').subscribe();
    expect(http.post).toHaveBeenCalledWith(`${BASE}/domain-verify/check`, { domain: 'acme.fr' });
  });
});
