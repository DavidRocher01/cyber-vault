import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { PublicScanResult } from './cyberscan.service';

const API = '/api/v1';

/** Domaine scan public (gratuit, sans auth) extrait de CyberscanService. */
@Injectable({ providedIn: 'root' })
export class PublicScanApiService {
  private http = inject(HttpClient);

  createPublicScan(url: string): Observable<PublicScanResult> {
    return this.http.post<PublicScanResult>(`${API}/public-scans`, { url });
  }

  getPublicScan(token: string): Observable<PublicScanResult> {
    return this.http.get<PublicScanResult>(`${API}/public-scans/${token}`);
  }
}
