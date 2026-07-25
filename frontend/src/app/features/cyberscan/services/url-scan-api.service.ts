import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { UrlScan, PaginatedUrlScans } from './cyberscan.service';

const API = '/api/v1';

/** Domaine scans d URL extrait de CyberscanService. */
@Injectable({ providedIn: 'root' })
export class UrlScanApiService {
  private http = inject(HttpClient);

  triggerUrlScan(url: string): Observable<UrlScan> {
    return this.http.post<UrlScan>(`${API}/url-scans`, { url });
  }

  getUrlScans(page = 1, perPage = 20): Observable<PaginatedUrlScans> {
    return this.http.get<PaginatedUrlScans>(`${API}/url-scans?page=${page}&per_page=${perPage}`);
  }

  getUrlScan(id: number): Observable<UrlScan> {
    return this.http.get<UrlScan>(`${API}/url-scans/${id}`);
  }

  deleteUrlScan(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/url-scans/${id}`);
  }

  downloadUrlScanPdfBlob(scanId: number): Observable<Blob> {
    return this.http.get(`${API}/url-scans/${scanId}/pdf`, { responseType: 'blob' });
  }
}
