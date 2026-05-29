import { Component, inject, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { AdminAuthService } from '../admin-auth.service';

interface WeekBucket {
  label: string;
  users: number;
  scans: number;
}
interface MonthBucket {
  label: string;
  cents: number;
}

interface Stats {
  users_total: number;
  active_subscriptions: number;
  newsletter_subscribers: number;
  bookings_this_month: number;
  new_contacts: number;
  recent_contacts: {
    id: number;
    name: string;
    email: string;
    need_type: string;
    status: string;
    created_at: string;
  }[];
  recent_bookings: {
    id: number;
    name: string;
    email: string;
    date: string;
    time: string;
    created_at: string;
  }[];
  weekly_activity: WeekBucket[];
  revenue_per_month: MonthBucket[];
}

@Component({
  standalone: true,
  selector: 'app-admin-dashboard',
  imports: [RouterLink, MatIconModule],
  templateUrl: './admin-dashboard.component.html',
})
export class AdminDashboardComponent implements OnInit {
  private http = inject(HttpClient);
  auth = inject(AdminAuthService);

  stats = signal<Stats | null>(null);
  loading = signal(true);

  ngOnInit() {
    this.http.get<Stats>('/api/v1/admin/stats', { headers: this.auth.headers() }).subscribe({
      next: s => {
        this.stats.set(s);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  maxWeekValue(): number {
    const w = this.stats()?.weekly_activity ?? [];
    return Math.max(1, ...w.map(b => Math.max(b.users, b.scans)));
  }

  maxRevenue(): number {
    const r = this.stats()?.revenue_per_month ?? [];
    return Math.max(1, ...r.map(b => b.cents));
  }

  totalRevenue(): number {
    return (this.stats()?.revenue_per_month ?? []).reduce((s, b) => s + b.cents, 0);
  }

  barHeight(value: number, max: number): number {
    return Math.round((value / max) * 100);
  }

  formatEur(cents: number): string {
    return (cents / 100).toLocaleString('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    });
  }

  needLabel(nt: string): string {
    const map: Record<string, string> = {
      'audit-flash': 'Audit Flash',
      'audit-app': 'App-Check',
      pentest: 'Pentest',
      abonnement: 'Abonnement',
      autre: 'Autre',
    };
    return map[nt] ?? nt;
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
