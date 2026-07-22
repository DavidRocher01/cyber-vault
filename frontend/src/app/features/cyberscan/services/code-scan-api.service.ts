import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { CodeScan, PaginatedCodeScans } from './cyberscan.service';

const API = '/api/v1';

/** Domaine scans de code extrait de CyberscanService. */
@Injectable({ providedIn: 'root' })
export class CodeScanApiService {
  private http = inject(HttpClient);

  triggerCodeScan(
    repoUrl: string,
    githubToken?: string
  ): Observable<{ scan_id: number; message: string }> {
    return this.http.post<{ scan_id: number; message: string }>(`${API}/code-scans`, {
      repo_url: repoUrl,
      github_token: githubToken || null,
    });
  }

  getCodeScans(page = 1, perPage = 10): Observable<PaginatedCodeScans> {
    return this.http.get<PaginatedCodeScans>(`${API}/code-scans?page=${page}&per_page=${perPage}`);
  }

  getCodeScan(id: number): Observable<CodeScan> {
    return this.http.get<CodeScan>(`${API}/code-scans/${id}`);
  }

  deleteCodeScan(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/code-scans/${id}`);
  }

  uploadCodeScan(file: File): Observable<{ scan_id: number; message: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ scan_id: number; message: string }>(
      `${API}/code-scans/upload`,
      formData
    );
  }
}
