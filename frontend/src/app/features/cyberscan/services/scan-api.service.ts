import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { Scan, PaginatedScans, FindingStatus } from './cyberscan.service';

const API = '/api/v1';

/** Domaine scans de site (declenchement, resultats, PDF, remediation, findings) extrait de CyberscanService. */
@Injectable({ providedIn: 'root' })
export class ScanApiService {
  private http = inject(HttpClient);

  triggerScan(siteId: number): Observable<{ scan_id: number; message: string }> {
    return this.http.post<{ scan_id: number; message: string }>(
      `${API}/scans/trigger/${siteId}`,
      {}
    );
  }

  getSiteScans(siteId: number, page = 1, perPage = 10): Observable<PaginatedScans> {
    return this.http.get<PaginatedScans>(
      `${API}/scans/site/${siteId}?page=${page}&per_page=${perPage}`
    );
  }

  getScan(scanId: number): Observable<Scan> {
    return this.http.get<Scan>(`${API}/scans/${scanId}`);
  }

  downloadPdf(scanId: number): string {
    return `${API}/scans/${scanId}/pdf`;
  }

  downloadPdfBlob(scanId: number): Observable<Blob> {
    return this.http.get(`${API}/scans/${scanId}/pdf`, { responseType: 'blob' });
  }

  downloadBrandedPdfBlob(scanId: number): Observable<Blob> {
    return this.http.get(`${API}/scans/${scanId}/pdf/branded`, { responseType: 'blob' });
  }

  downloadRemediationBlob(scanId: number, scriptKey: string): Observable<Blob> {
    return this.http.get(`${API}/scans/${scanId}/remediation/${scriptKey}`, {
      responseType: 'blob',
    });
  }

  getFindingStatuses(siteId: number): Observable<FindingStatus[]> {
    return this.http.get<FindingStatus[]>(`${API}/scans/site/${siteId}/finding-status`);
  }

  updateFindingStatus(
    siteId: number,
    moduleKey: string,
    status: string,
    note?: string
  ): Observable<FindingStatus> {
    return this.http.put<FindingStatus>(`${API}/scans/site/${siteId}/finding-status/${moduleKey}`, {
      status,
      note: note ?? null,
    });
  }
}
