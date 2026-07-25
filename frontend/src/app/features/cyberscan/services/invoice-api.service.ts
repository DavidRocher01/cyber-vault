import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { Invoice, PaginatedInvoices } from './cyberscan.service';

const API = '/api/v1';

/**
 * Domaine « factures » extrait de CyberscanService (service fourre-tout).
 * Premier découpage pilote : borne domaine claire, un seul consommateur.
 */
@Injectable({ providedIn: 'root' })
export class InvoiceApiService {
  private http = inject(HttpClient);

  getMyInvoices(page = 1, perPage = 20): Observable<PaginatedInvoices> {
    return this.http.get<PaginatedInvoices>(`${API}/invoices?page=${page}&per_page=${perPage}`);
  }

  getInvoice(id: number): Observable<Invoice> {
    return this.http.get<Invoice>(`${API}/invoices/${id}`);
  }

  downloadInvoicePdfBlob(id: number): Observable<Blob> {
    return this.http.get(`${API}/invoices/${id}/pdf`, { responseType: 'blob' });
  }
}
