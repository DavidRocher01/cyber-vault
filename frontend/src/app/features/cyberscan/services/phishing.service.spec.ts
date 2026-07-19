import { describe, it, expect, vi } from 'vitest';
import { of } from 'rxjs';
import { PhishingService, planMaxScenarios, planMaxTargets } from './phishing.service';

const BASE = '/api/v1/phishing';

function makeService(
  httpOverrides: Partial<{ get: any; post: any; patch: any; delete: any }> = {}
) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    patch: vi.fn().mockReturnValue(of({})),
    delete: vi.fn().mockReturnValue(of(undefined)),
    ...httpOverrides,
  };
  const service = Object.create(PhishingService.prototype) as PhishingService;
  (service as any).http = http;
  (service as any).base = BASE;
  return { service, http };
}

describe('PhishingService — downloadPdfBlob()', () => {
  it('appelle GET /campaigns/{id}/pdf en responseType blob (Bearer via intercepteur)', () => {
    const { service, http } = makeService();
    service.downloadPdfBlob(42).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${BASE}/campaigns/42/pdf`, { responseType: 'blob' });
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

describe('PhishingService — cibles (Lot 2) + cancel (Lot 3)', () => {
  it('getTargets appelle GET /campaigns/{id}/targets', () => {
    const { service, http } = makeService();
    service.getTargets(7).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${BASE}/campaigns/7/targets`);
  });

  it('addTarget appelle POST /campaigns/{id}/targets/single', () => {
    const { service, http } = makeService();
    service.addTarget(7, { email: 'a@x.com' }).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${BASE}/campaigns/7/targets/single`, {
      email: 'a@x.com',
    });
  });

  it('deleteTarget appelle DELETE /campaigns/{id}/targets/{tid}', () => {
    const { service, http } = makeService();
    service.deleteTarget(7, 3).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${BASE}/campaigns/7/targets/3`);
  });

  it('uploadTargets en merge (défaut) : pas de query replace', () => {
    const { service, http } = makeService();
    service.uploadTargets(7, new File([''], 't.csv')).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${BASE}/campaigns/7/targets`, expect.any(FormData));
  });

  it('uploadTargets(replace=true) ajoute ?replace=true', () => {
    const { service, http } = makeService();
    service.uploadTargets(7, new File([''], 't.csv'), true).subscribe();
    expect(http.post).toHaveBeenCalledWith(
      `${BASE}/campaigns/7/targets?replace=true`,
      expect.any(FormData)
    );
  });

  it('cancelCampaign appelle POST /campaigns/{id}/cancel', () => {
    const { service, http } = makeService();
    service.cancelCampaign(7).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${BASE}/campaigns/7/cancel`, {});
  });

  it('deleteCampaign appelle DELETE /campaigns/{id}', () => {
    const { service, http } = makeService();
    service.deleteCampaign(7).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${BASE}/campaigns/7`);
  });
});

describe('PhishingService — launchWithCgu() (R4)', () => {
  it('PATCH avec cgu_accepted:true puis POST /launch', () => {
    const { service, http } = makeService();
    service.launchWithCgu(9, { name: 'X' }).subscribe();
    expect(http.patch).toHaveBeenCalledWith(`${BASE}/campaigns/9`, {
      name: 'X',
      cgu_accepted: true,
    });
    expect(http.post).toHaveBeenCalledWith(`${BASE}/campaigns/9/launch`, {});
  });

  it('accepte un patch vide (juste cgu_accepted)', () => {
    const { service, http } = makeService();
    service.launchWithCgu(9).subscribe();
    expect(http.patch).toHaveBeenCalledWith(`${BASE}/campaigns/9`, { cgu_accepted: true });
  });
});

describe('PhishingService — plafonds de plan (PHISHING_PLAN_CONFIG)', () => {
  it('planMaxScenarios : valeurs par plan', () => {
    expect(planMaxScenarios('express')).toBe(2);
    expect(planMaxScenarios('standard')).toBe(5);
    expect(planMaxScenarios('premium')).toBe(10);
    expect(planMaxScenarios('quarterly')).toBe(3);
    expect(planMaxScenarios('monthly')).toBe(7);
  });
  it('planMaxScenarios : repli à 2 (inconnu / null)', () => {
    expect(planMaxScenarios('unknown')).toBe(2);
    expect(planMaxScenarios(null)).toBe(2);
    expect(planMaxScenarios(undefined)).toBe(2);
  });
  it('planMaxTargets : valeurs par plan + repli à 50', () => {
    expect(planMaxTargets('express')).toBe(50);
    expect(planMaxTargets('premium')).toBe(500);
    expect(planMaxTargets('monthly')).toBe(300);
    expect(planMaxTargets('unknown')).toBe(50);
    expect(planMaxTargets(null)).toBe(50);
  });
});
