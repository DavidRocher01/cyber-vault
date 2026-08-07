import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { ComplianceAssessment, PieceJustificative } from './cyberscan.service';

const API = '/api/v1';

/** Domaine conformite NIS2 / ISO 27001 (auto-evaluation + PDF) extrait de CyberscanService. */
@Injectable({ providedIn: 'root' })
export class ComplianceApiService {
  private http = inject(HttpClient);

  /** Préfixe des routes NIS2 selon le SUJET de l'évaluation.
   *
   *  `null` → la mienne. Un identifiant → le dossier que je monte pour ce
   *  client, côté console RSSI.
   *
   *  Les deux familles de routes ont volontairement les mêmes suffixes
   *  (`/criteres/…`, `/pieces/…`, `/pdf/auditor`) : c'est ce qui permet à un
   *  seul composant de servir les deux sujets sans dupliquer une ligne.
   */
  private baseNis2(clientId?: number | null): string {
    return clientId == null ? `${API}/nis2/me` : `${API}/rssi/clients/${clientId}/nis2`;
  }

  getNis2Assessment(clientId?: number | null): Observable<ComplianceAssessment> {
    return this.http.get<ComplianceAssessment>(this.baseNis2(clientId));
  }

  saveNis2Assessment(
    items: Record<string, string>,
    clientId?: number | null
  ): Observable<ComplianceAssessment> {
    return this.http.put<ComplianceAssessment>(this.baseNis2(clientId), { items });
  }

  /** Dépose un document et le rattache à un critère, en un seul appel.
   *
   *  Un seul appel côté serveur aussi : déposer puis rattacher en deux temps
   *  ouvrirait une fenêtre pendant laquelle le fichier n'est référencé par rien,
   *  et la purge des orphelins finirait par l'effacer.
   */
  deposerPiece(
    itemId: string,
    fichier: File,
    clientId?: number | null
  ): Observable<PieceJustificative> {
    const corps = new FormData();
    corps.append('fichier', fichier);
    return this.http.post<PieceJustificative>(
      `${this.baseNis2(clientId)}/criteres/${encodeURIComponent(itemId)}/pieces`,
      corps
    );
  }

  retirerPiece(pieceId: number, clientId?: number | null): Observable<void> {
    return this.http.delete<void>(`${this.baseNis2(clientId)}/pieces/${pieceId}`);
  }

  lienPiece(pieceId: number, clientId?: number | null): Observable<{ url: string }> {
    return this.http.get<{ url: string }>(`${this.baseNis2(clientId)}/pieces/${pieceId}/download`);
  }

  downloadNis2PdfBlob(): Observable<Blob> {
    return this.http.get(`${API}/nis2/me/pdf`, { responseType: 'blob' });
  }

  downloadNis2AuditorPdfBlob(clientId?: number | null): Observable<Blob> {
    return this.http.get(`${this.baseNis2(clientId)}/pdf/auditor`, { responseType: 'blob' });
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
