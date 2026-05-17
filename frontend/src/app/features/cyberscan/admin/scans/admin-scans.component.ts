import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AdminAuthService } from '../admin-auth.service';

interface AdminScan {
  id: number;
  target_url: string;
  status: string;
  overall_status: string | null;
  created_at: string;
  finished_at: string | null;
  error_message: string | null;
}

@Component({
  standalone: true,
  selector: 'app-admin-scans',
  templateUrl: './admin-scans.component.html',
})
export class AdminScansComponent implements OnInit {
  private http = inject(HttpClient);
  auth = inject(AdminAuthService);

  scans = signal<AdminScan[]>([]);
  loading = signal(true);
  filter = signal<'all' | 'completed' | 'failed' | 'pending'>('all');

  filtered = computed(() => {
    const f = this.filter();
    if (f === 'all') return this.scans();
    if (f === 'completed') return this.scans().filter(s => s.overall_status === 'safe' || s.overall_status === 'warning' || s.overall_status === 'danger');
    if (f === 'failed') return this.scans().filter(s => s.status === 'failed' || s.error_message);
    return this.scans().filter(s => s.status === 'pending' || s.status === 'running');
  });

  ngOnInit() {
    this.http.get<AdminScan[]>('/api/v1/admin/scans', { headers: this.auth.headers() }).subscribe({
      next: s => { this.scans.set(s); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  statusColor(status: string): string {
    const map: Record<string, string> = {
      completed: 'bg-emerald-900/30 text-emerald-400',
      failed: 'bg-red-900/30 text-red-400',
      running: 'bg-blue-900/30 text-blue-400',
      pending: 'bg-gray-700 text-gray-400',
    };
    return map[status] ?? 'bg-gray-700 text-gray-400';
  }

  overallColor(overall: string | null): string {
    const map: Record<string, string> = {
      safe: 'bg-emerald-900/30 text-emerald-400',
      warning: 'bg-yellow-900/30 text-yellow-400',
      danger: 'bg-red-900/30 text-red-400',
    };
    return map[overall ?? ''] ?? 'bg-gray-700 text-gray-400';
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  truncate(url: string, max = 50): string {
    return url.length > max ? url.slice(0, max) + '…' : url;
  }
}
