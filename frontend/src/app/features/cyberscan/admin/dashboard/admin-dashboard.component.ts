import { Component, inject, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { AdminAuthService } from '../admin-auth.service';

interface Stats {
  users_total: number;
  active_subscriptions: number;
  newsletter_subscribers: number;
  bookings_this_month: number;
  new_contacts: number;
  recent_contacts: { id: number; name: string; email: string; need_type: string; status: string; created_at: string }[];
  recent_bookings: { id: number; name: string; email: string; date: string; time: string; created_at: string }[];
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
      next: s => { this.stats.set(s); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  needLabel(nt: string): string {
    const map: Record<string, string> = {
      'audit-flash': 'Audit Flash', 'audit-app': 'App-Check',
      'pentest': 'Pentest', 'abonnement': 'Abonnement', 'autre': 'Autre',
    };
    return map[nt] ?? nt;
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  }
}
