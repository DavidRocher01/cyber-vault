import { Injectable, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { lireProvenance } from '../../../core/services/provenance.service';
import { PublicScanResult } from './cyberscan.service';

const API = '/api/v1';

/** Domaine scan public (gratuit, sans auth) extrait de CyberscanService. */
@Injectable({ providedIn: 'root' })
export class PublicScanApiService {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);

  createPublicScan(url: string): Observable<PublicScanResult> {
    // Premiere etape du tunnel : c'est le seul instant ou la campagne est encore
    // lisible dans l'URL. Rien n'est stocke, donc rien a relire plus tard.
    return this.http.post<PublicScanResult>(`${API}/public-scans`, {
      url,
      ...lireProvenance(isPlatformBrowser(this.platformId)),
    });
  }

  getPublicScan(token: string): Observable<PublicScanResult> {
    return this.http.get<PublicScanResult>(`${API}/public-scans/${token}`);
  }

  /** Débloque le rapport complet contre un email + consentement RGPD. */
  unlockPublicScan(token: string, email: string, consent: boolean): Observable<PublicScanResult> {
    return this.http.post<PublicScanResult>(`${API}/public-scans/${token}/unlock`, {
      email,
      consent,
    });
  }
}
