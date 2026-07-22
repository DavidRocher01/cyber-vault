import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  Site,
  SiteCreate,
  SiteDomainStatus,
  SiteDomainVerify,
  SubdomainResult,
} from './cyberscan.service';

const API = '/api/v1';

/** Domaine sites (CRUD, verification de domaine, sous-domaines) extrait de CyberscanService. */
@Injectable({ providedIn: 'root' })
export class SiteApiService {
  private http = inject(HttpClient);

  getMySites(): Observable<Site[]> {
    return this.http.get<Site[]>(`${API}/sites`);
  }

  createSite(data: SiteCreate): Observable<Site> {
    return this.http.post<Site>(`${API}/sites`, data);
  }

  deleteSite(siteId: number): Observable<void> {
    return this.http.delete<void>(`${API}/sites/${siteId}`);
  }

  getSiteDomainStatus(siteId: number): Observable<SiteDomainStatus> {
    return this.http.get<SiteDomainStatus>(`${API}/sites/${siteId}/domain`);
  }

  requestSiteDomainVerify(siteId: number): Observable<SiteDomainVerify> {
    return this.http.post<SiteDomainVerify>(`${API}/sites/${siteId}/domain/verify`, {});
  }

  checkSiteDomainVerify(siteId: number): Observable<SiteDomainStatus> {
    return this.http.post<SiteDomainStatus>(`${API}/sites/${siteId}/domain/verify/check`, {});
  }

  getSiteSubdomains(siteId: number): Observable<SubdomainResult> {
    return this.http.get<SubdomainResult>(`${API}/sites/${siteId}/subdomains`);
  }
}
