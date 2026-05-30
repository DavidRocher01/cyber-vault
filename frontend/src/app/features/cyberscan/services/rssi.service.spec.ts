import { describe, it, expect, vi } from 'vitest';
import { of } from 'rxjs';
import { RssiService } from './rssi.service';

const API = '/api/v1/rssi';

function makeService(
  httpOverrides: Partial<{ get: any; post: any; delete: any; put: any; patch: any }> = {}
) {
  const http = {
    get: vi.fn().mockReturnValue(of({})),
    post: vi.fn().mockReturnValue(of({})),
    delete: vi.fn().mockReturnValue(of(undefined)),
    put: vi.fn().mockReturnValue(of({})),
    patch: vi.fn().mockReturnValue(of({})),
    ...httpOverrides,
  };
  const service = Object.create(RssiService.prototype) as RssiService;
  (service as any).http = http;
  return { service, http };
}

// ── Clients ───────────────────────────────────────────────────────────────────

describe('RssiService — getClients()', () => {
  it('appelle GET /rssi/clients', () => {
    const { service, http } = makeService();
    service.getClients().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients`);
  });
});

describe('RssiService — getClient()', () => {
  it('appelle GET /rssi/clients/:id', () => {
    const { service, http } = makeService();
    service.getClient(42).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/42`);
  });
});

describe('RssiService — createClient()', () => {
  it('appelle POST /rssi/clients', () => {
    const { service, http } = makeService();
    service.createClient({ name: 'Acme' }).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/clients`, { name: 'Acme' });
  });
});

describe('RssiService — updateClient()', () => {
  it('appelle PUT /rssi/clients/:id', () => {
    const { service, http } = makeService();
    service.updateClient(5, { name: 'Updated' }).subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/clients/5`, { name: 'Updated' });
  });
});

describe('RssiService — deleteClient()', () => {
  it('appelle DELETE /rssi/clients/:id', () => {
    const { service, http } = makeService();
    service.deleteClient(3).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/clients/3`);
  });
});

// ── Visits ────────────────────────────────────────────────────────────────────

describe('RssiService — getVisits()', () => {
  it('appelle GET /rssi/clients/:id/visits', () => {
    const { service, http } = makeService();
    service.getVisits(10).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/10/visits`);
  });
});

describe('RssiService — createVisit()', () => {
  it('appelle POST /rssi/clients/:id/visits', () => {
    const { service, http } = makeService();
    service.createVisit(10, { scheduled_date: '2025-06-01' }).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/clients/10/visits`, {
      scheduled_date: '2025-06-01',
    });
  });
});

describe('RssiService — updateVisit()', () => {
  it('appelle PUT /rssi/clients/:id/visits/:vid', () => {
    const { service, http } = makeService();
    service.updateVisit(10, 7, { status: 'completed' }).subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/clients/10/visits/7`, { status: 'completed' });
  });
});

describe('RssiService — deleteVisit()', () => {
  it('appelle DELETE /rssi/clients/:id/visits/:vid', () => {
    const { service, http } = makeService();
    service.deleteVisit(10, 7).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/clients/10/visits/7`);
  });
});

// ── Actions ───────────────────────────────────────────────────────────────────

describe('RssiService — getActions()', () => {
  it('appelle GET /rssi/clients/:id/actions sans filtre', () => {
    const { service, http } = makeService();
    service.getActions(2).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/2/actions`, { params: {} });
  });

  it('appelle GET avec status_filter', () => {
    const { service, http } = makeService();
    service.getActions(2, 'open').subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/2/actions`, {
      params: { status_filter: 'open' },
    });
  });
});

describe('RssiService — createAction()', () => {
  it('appelle POST /rssi/clients/:id/actions', () => {
    const { service, http } = makeService();
    service.createAction(2, { title: 'Patch SSL' }).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/clients/2/actions`, { title: 'Patch SSL' });
  });
});

describe('RssiService — updateAction()', () => {
  it('appelle PUT /rssi/clients/:id/actions/:aid', () => {
    const { service, http } = makeService();
    service.updateAction(2, 9, { status: 'done' }).subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/clients/2/actions/9`, { status: 'done' });
  });
});

describe('RssiService — deleteAction()', () => {
  it('appelle DELETE /rssi/clients/:id/actions/:aid', () => {
    const { service, http } = makeService();
    service.deleteAction(2, 9).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/clients/2/actions/9`);
  });
});

// ── Dashboard ─────────────────────────────────────────────────────────────────

describe('RssiService — getDashboardOverview()', () => {
  it('appelle GET /rssi/dashboard/overview', () => {
    const { service, http } = makeService();
    service.getDashboardOverview().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/dashboard/overview`);
  });
});

describe('RssiService — getClientsSummary()', () => {
  it('appelle GET /rssi/dashboard/clients-summary', () => {
    const { service, http } = makeService();
    service.getClientsSummary().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/dashboard/clients-summary`);
  });
});

describe('RssiService — getDashboardAlerts()', () => {
  it('appelle GET /rssi/dashboard/alerts', () => {
    const { service, http } = makeService();
    service.getDashboardAlerts().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/dashboard/alerts`);
  });
});

describe('RssiService — getUpcomingEvents()', () => {
  it('appelle GET avec days_ahead=14 par défaut', () => {
    const { service, http } = makeService();
    service.getUpcomingEvents().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/dashboard/upcoming-events`, {
      params: { days_ahead: 14 },
    });
  });

  it('appelle GET avec days_ahead=30', () => {
    const { service, http } = makeService();
    service.getUpcomingEvents(30).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/dashboard/upcoming-events`, {
      params: { days_ahead: 30 },
    });
  });
});

describe('RssiService — getSuggestions()', () => {
  it('appelle GET /rssi/dashboard/suggestions', () => {
    const { service, http } = makeService();
    service.getSuggestions().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/dashboard/suggestions`);
  });
});

// ── Profile ───────────────────────────────────────────────────────────────────

describe('RssiService — getProfile()', () => {
  it('appelle GET /rssi/profile', () => {
    const { service, http } = makeService();
    service.getProfile().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/profile`);
  });
});

describe('RssiService — updateProfile()', () => {
  it('appelle PATCH /rssi/profile', () => {
    const { service, http } = makeService();
    service.updateProfile({ display_name: 'Alice' }).subscribe();
    expect(http.patch).toHaveBeenCalledWith(`${API}/profile`, { display_name: 'Alice' });
  });
});

// ── Sites ─────────────────────────────────────────────────────────────────────

describe('RssiService — getClientSites()', () => {
  it('appelle GET /rssi/clients/:id/sites', () => {
    const { service, http } = makeService();
    service.getClientSites(4).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/4/sites`);
  });
});

describe('RssiService — getUnlinkedSites()', () => {
  it('appelle GET /rssi/sites/unlinked', () => {
    const { service, http } = makeService();
    service.getUnlinkedSites().subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/sites/unlinked`);
  });
});

describe('RssiService — linkSite()', () => {
  it('appelle PUT /rssi/clients/:id/sites/:sid', () => {
    const { service, http } = makeService();
    service.linkSite(4, 11).subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/clients/4/sites/11`, {});
  });
});

describe('RssiService — unlinkSite()', () => {
  it('appelle DELETE /rssi/clients/:id/sites/:sid', () => {
    const { service, http } = makeService();
    service.unlinkSite(4, 11).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/clients/4/sites/11`);
  });
});

// ── Deliverables ──────────────────────────────────────────────────────────────

describe('RssiService — getDeliverables()', () => {
  it('appelle GET /rssi/clients/:id/deliverables', () => {
    const { service, http } = makeService();
    service.getDeliverables(6).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/6/deliverables`);
  });
});

describe('RssiService — createDeliverable()', () => {
  it('appelle POST /rssi/clients/:id/deliverables', () => {
    const { service, http } = makeService();
    service.createDeliverable(6, { title: 'Rapport Q1', delivered_at: '2025-03-31' }).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/clients/6/deliverables`, {
      title: 'Rapport Q1',
      delivered_at: '2025-03-31',
    });
  });
});

describe('RssiService — updateDeliverable()', () => {
  it('appelle PUT /rssi/clients/:id/deliverables/:did', () => {
    const { service, http } = makeService();
    service.updateDeliverable(6, 13, { title: 'Rapport Q1 v2' }).subscribe();
    expect(http.put).toHaveBeenCalledWith(`${API}/clients/6/deliverables/13`, {
      title: 'Rapport Q1 v2',
    });
  });
});

describe('RssiService — deleteDeliverable()', () => {
  it('appelle DELETE /rssi/clients/:id/deliverables/:did', () => {
    const { service, http } = makeService();
    service.deleteDeliverable(6, 13).subscribe();
    expect(http.delete).toHaveBeenCalledWith(`${API}/clients/6/deliverables/13`);
  });
});

describe('RssiService — getDeliverableDownloadUrl()', () => {
  it('appelle GET /rssi/clients/:id/deliverables/:did/download', () => {
    const { service, http } = makeService();
    service.getDeliverableDownloadUrl(6, 13).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/6/deliverables/13/download`);
  });
});

// ── CSV / Activity ────────────────────────────────────────────────────────────

describe('RssiService — exportActionsCsv()', () => {
  it('appelle GET /rssi/clients/:id/actions/export avec responseType blob', () => {
    const { service, http } = makeService();
    service.exportActionsCsv(8).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/8/actions/export`, {
      responseType: 'blob',
    });
  });
});

describe('RssiService — logActivity()', () => {
  it('appelle POST /rssi/clients/:id/activity', () => {
    const { service, http } = makeService();
    service.logActivity(3, { action_type: 'view_client' }).subscribe();
    expect(http.post).toHaveBeenCalledWith(`${API}/clients/3/activity`, {
      action_type: 'view_client',
    });
  });
});

describe('RssiService — getActivityLog()', () => {
  it('appelle GET /rssi/clients/:id/activity avec limit=50 par défaut', () => {
    const { service, http } = makeService();
    service.getActivityLog(3).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/3/activity`, { params: { limit: 50 } });
  });

  it('appelle GET avec limit personnalisé', () => {
    const { service, http } = makeService();
    service.getActivityLog(3, 20).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/3/activity`, { params: { limit: 20 } });
  });
});

describe('RssiService — downloadReport()', () => {
  it('appelle GET /rssi/clients/:id/report avec responseType blob', () => {
    const { service, http } = makeService();
    service.downloadReport(5).subscribe();
    expect(http.get).toHaveBeenCalledWith(`${API}/clients/5/report`, { responseType: 'blob' });
  });
});
