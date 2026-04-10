import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { interval, Subscription as RxSubscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import { CyberscanService, CodeScan, PaginatedCodeScans } from '../services/cyberscan.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

interface Finding {
  tool: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  rule: string;
  title: string;
  message: string;
  file: string;
  line: number | null;
  confidence: string;
  fix_versions?: string[];
}

interface ScanResults {
  findings: Finding[];
  summary: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

@Component({
  selector: 'app-code-scan',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule,
    MatSnackBarModule, MatPaginatorModule, NavButtonsComponent,
  ],
  templateUrl: './code-scan.component.html',
})
export class CodeScanComponent implements OnInit, OnDestroy {
  private cyberscan = inject(CyberscanService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private pollSubs: RxSubscription[] = [];

  form = this.fb.nonNullable.group({
    repo_url: ['', [Validators.required, Validators.pattern(/^https?:\/\/.+/)]],
    github_token: [''],
    show_token: [false],
  });

  submitting = signal(false);
  history = signal<PaginatedCodeScans | null>(null);
  loadingHistory = signal(true);
  currentPage = signal(1);
  activeScan = signal<CodeScan | null>(null);
  showTokenField = signal(false);
  activeTab = signal<'critical' | 'high' | 'medium' | 'low' | 'all'>('all');
  mode = signal<'git' | 'zip'>('git');
  selectedFile = signal<File | null>(null);
  dragOver = signal(false);

  ngOnInit() {
    this.loadHistory(1);
  }

  ngOnDestroy() {
    this.pollSubs.forEach(s => s.unsubscribe());
  }

  loadHistory(page: number) {
    this.loadingHistory.set(true);
    this.currentPage.set(page);
    this.cyberscan.getCodeScans(page, 10).subscribe({
      next: data => {
        this.history.set(data);
        this.loadingHistory.set(false);
        data.items
          .filter(s => s.status === 'pending' || s.status === 'running')
          .forEach(s => this.startPolling(s.id));
      },
      error: () => this.loadingHistory.set(false),
    });
  }

  onPageChange(event: PageEvent) {
    this.loadHistory(event.pageIndex + 1);
  }

  setMode(m: 'git' | 'zip') {
    this.mode.set(m);
    this.selectedFile.set(null);
    this.dragOver.set(false);
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    if (file && !file.name.toLowerCase().endsWith('.zip')) {
      this.snack.open('Seuls les fichiers .zip sont acceptés', 'Fermer', { duration: 4000 });
      return;
    }
    this.selectedFile.set(file);
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.dragOver.set(false);
    const file = event.dataTransfer?.files[0] ?? null;
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.zip')) {
      this.snack.open('Seuls les fichiers .zip sont acceptés', 'Fermer', { duration: 4000 });
      return;
    }
    this.selectedFile.set(file);
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.dragOver.set(true);
  }

  onDragLeave() {
    this.dragOver.set(false);
  }

  trimRepoUrl() {
    const ctrl = this.form.controls.repo_url;
    ctrl.setValue(ctrl.value.trim(), { emitEvent: false });
  }

  submit() {
    if (this.mode() === 'zip') {
      this.submitZip();
      return;
    }
    if (this.form.invalid || this.submitting()) return;
    this.submitting.set(true);
    const { repo_url, github_token } = this.form.getRawValue();

    this.cyberscan.triggerCodeScan(repo_url, github_token || undefined).subscribe({
      next: res => {
        this.submitting.set(false);
        this.form.patchValue({ repo_url: '', github_token: '' });
        this.snack.open('Analyse lancée — résultats dans quelques minutes', 'OK', { duration: 6000 });
        this.loadHistory(1);
        this.startPolling(res.scan_id);
      },
      error: err => {
        this.submitting.set(false);
        this.snack.open(err.error?.detail || 'Erreur lors du lancement', 'Fermer', { duration: 6000 });
      },
    });
  }

  submitZip() {
    const file = this.selectedFile();
    if (!file || this.submitting()) return;
    this.submitting.set(true);
    this.cyberscan.uploadCodeScan(file).subscribe({
      next: res => {
        this.submitting.set(false);
        this.selectedFile.set(null);
        this.snack.open('Analyse lancée — résultats dans quelques minutes', 'OK', { duration: 6000 });
        this.loadHistory(1);
        this.startPolling(res.scan_id);
      },
      error: err => {
        this.submitting.set(false);
        this.snack.open(err.error?.detail || 'Erreur lors de l\'upload', 'Fermer', { duration: 6000 });
      },
    });
  }

  startPolling(scanId: number) {
    const sub = interval(4000).pipe(
      switchMap(() => this.cyberscan.getCodeScan(scanId)),
      takeWhile(s => s.status === 'pending' || s.status === 'running', true),
    ).subscribe(scan => {
      this.history.update(h => h ? {
        ...h,
        items: h.items.map(s => s.id === scan.id ? scan : s),
      } : h);
      if (this.activeScan()?.id === scan.id) {
        this.activeScan.set(scan);
      }
    });
    this.pollSubs.push(sub);
  }

  viewScan(scan: CodeScan) {
    this.activeScan.set(scan);
    this.activeTab.set('all');
  }

  deleteScan(scan: CodeScan) {
    this.cyberscan.deleteCodeScan(scan.id).subscribe({
      next: () => {
        this.history.update(h => h ? {
          ...h,
          items: h.items.filter(s => s.id !== scan.id),
          total: h.total - 1,
        } : h);
        if (this.activeScan()?.id === scan.id) this.activeScan.set(null);
      },
    });
  }

  getResults(scan: CodeScan): ScanResults | null {
    if (!scan.results_json) return null;
    try { return JSON.parse(scan.results_json); } catch { return null; }
  }

  filteredFindings(results: ScanResults): Finding[] {
    const tab = this.activeTab();
    if (tab === 'all') return results.findings;
    return results.findings.filter(f => f.severity === tab);
  }

  severityColor(sev: string): string {
    switch (sev) {
      case 'critical': return 'text-red-400 bg-red-400/10 border-red-700';
      case 'high':     return 'text-orange-400 bg-orange-400/10 border-orange-700';
      case 'medium':   return 'text-yellow-400 bg-yellow-400/10 border-yellow-700';
      default:         return 'text-gray-400 bg-gray-700/30 border-gray-600';
    }
  }

  severityLabel(sev: string): string {
    const map: Record<string, string> = { critical: 'Critique', high: 'Élevé', medium: 'Moyen', low: 'Faible' };
    return map[sev] ?? sev;
  }

  severityIcon(sev: string): string {
    switch (sev) {
      case 'critical': return 'dangerous';
      case 'high':     return 'error';
      case 'medium':   return 'warning';
      default:         return 'info';
    }
  }

  toolBadge(tool: string): string {
    switch (tool) {
      case 'bandit':         return 'bg-purple-900/40 border-purple-700 text-purple-300';
      case 'semgrep':        return 'bg-blue-900/40 border-blue-700 text-blue-300';
      case 'pip-audit':      return 'bg-yellow-900/40 border-yellow-700 text-yellow-300';
      case 'gitleaks':       return 'bg-red-900/40 border-red-700 text-red-300';
      case 'detect-secrets': return 'bg-pink-900/40 border-pink-700 text-pink-300';
      case 'npm-audit':      return 'bg-green-900/40 border-green-700 text-green-300';
      case 'trivy':          return 'bg-cyan-900/40 border-cyan-700 text-cyan-300';
      case 'checkov':        return 'bg-orange-900/40 border-orange-700 text-orange-300';
      default:               return 'bg-gray-700/30 border-gray-600 text-gray-400';
    }
  }

  statusColor(status: string): string {
    switch (status) {
      case 'done':    return 'text-green-400';
      case 'running': return 'text-cyan-400';
      case 'pending': return 'text-yellow-400';
      case 'failed':  return 'text-red-400';
      default:        return 'text-gray-400';
    }
  }

  statusLabel(status: string): string {
    const map: Record<string, string> = { done: 'Terminé', running: 'En cours', pending: 'En attente', failed: 'Échec' };
    return map[status] ?? status;
  }

  statusBadgeClass(status: string): string {
    switch (status) {
      case 'done':    return 'text-green-400 bg-green-400/10 border-green-700';
      case 'running': return 'text-cyan-400 bg-cyan-400/10 border-cyan-700';
      case 'pending': return 'text-yellow-400 bg-yellow-400/10 border-yellow-700';
      case 'failed':  return 'text-red-400 bg-red-400/10 border-red-700';
      default:        return 'text-gray-400 bg-gray-700/30 border-gray-600';
    }
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  totalFindings(scan: CodeScan): number {
    return scan.critical_count + scan.high_count + scan.medium_count + scan.low_count;
  }

  get isRunning(): boolean {
    const s = this.activeScan();
    return !!s && (s.status === 'pending' || s.status === 'running');
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}
