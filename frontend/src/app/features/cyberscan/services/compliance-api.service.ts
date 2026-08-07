import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { ComplianceAssessment, PieceJustificative } from './cyberscan.service';

const API = '/api/v1';

/** Domaine conformite NIS2 / ISO 27001 (auto-evaluation + PDF) extrait de CyberscanService. */
@Injectable({ providedIn: 'root' })
export class ComplianceApiService {
  private http = inject(HttpClient);

  getNis2Assessment(): Observable<ComplianceAssessment> {
    return this.http.get<ComplianceAssessment>(`${API}/nis2/me`);
  }

  saveNis2Assessment(items: Record<string, string>): Observable<ComplianceAssessment> {
    return this.http.put<ComplianceAssessment>(`${API}/nis2/me`, { items });
  }

  /** Dépose un document et le rattache à un critère, en un seul appel.
   *
   *  Un seul appel côté serveur aussi : déposer puis rattacher en deux temps
   *  ouvrirait une fenêtre pendant laquelle le fichier n'est référencé par rien,
   *  et la purge des orphelins finirait par l'effacer.
   */
  deposerPiece(itemId: string, fichier: File): Observable<PieceJustificative> {
    const corps = new FormData();
    corps.append('fichier', fichier);
    return this.http.post<PieceJustificative>(
      `${API}/nis2/me/criteres/${encodeURIComponent(itemId)}/pieces`,
      corps
    );
  }

  retirerPiece(pieceId: number): Observable<void> {
    return this.http.delete<void>(`${API}/nis2/me/pieces/${pieceId}`);
  }

  lienPiece(pieceId: number): Observable<{ url: string }> {
    return this.http.get<{ url: string }>(`${API}/nis2/me/pieces/${pieceId}/download`);
  }

  downloadNis2PdfBlob(): Observable<Blob> {
    return this.http.get(`${API}/nis2/me/pdf`, { responseType: 'blob' });
  }

  downloadNis2AuditorPdfBlob(): Observable<Blob> {
    return this.http.get(`${API}/nis2/me/pdf/auditor`, { responseType: 'blob' });
  }

  getIso27001Assessment(): Observable<ComplianceAssessment> {
    return this.http.get<ComplianceAssessment>(`${API}/iso27001/me`);
  }

  saveIso27001Assessment(items: Record<string, string>): Observable<ComplianceAssessment> {
    return this.http.put<ComplianceAssessment>(`${API}/iso27001/me`, { items });
  }

  downloadIso27001PdfBlob(): Observable<Blob> {
    return this.http.get(`${API}/iso27001/me/pdf`, { responseType: 'blob' });
  }
}
