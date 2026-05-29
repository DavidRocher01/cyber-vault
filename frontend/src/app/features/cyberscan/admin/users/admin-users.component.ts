import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { AdminAuthService } from '../admin-auth.service';

interface AdminUser {
  id: number;
  email: string;
  is_active: boolean;
  is_rssi_consultant: boolean;
  plan: string;
  plan_name: string | null;
  subscription_status: string | null;
  subscription_since: string | null;
}

@Component({
  standalone: true,
  selector: 'app-admin-users',
  imports: [MatIconModule],
  templateUrl: './admin-users.component.html',
})
export class AdminUsersComponent implements OnInit {
  private http = inject(HttpClient);
  auth = inject(AdminAuthService);

  users = signal<AdminUser[]>([]);
  loading = signal(true);
  search = signal('');

  filtered = computed(() => {
    const q = this.search().toLowerCase();
    return q ? this.users().filter(u => u.email.toLowerCase().includes(q)) : this.users();
  });

  planCounts = computed(() => {
    const counts: Record<string, number> = { free: 0, starter: 0, pro: 0, business: 0 };
    for (const u of this.users()) {
      const k = u.plan_name ?? 'free';
      counts[k] = (counts[k] ?? 0) + 1;
    }
    return counts;
  });

  ngOnInit() {
    this.http.get<AdminUser[]>('/api/v1/admin/users', { headers: this.auth.headers() }).subscribe({
      next: u => {
        this.users.set(u);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  planColor(plan: string | null): string {
    const map: Record<string, string> = {
      starter: 'bg-blue-900/30 text-blue-400',
      pro: 'bg-purple-900/30 text-purple-400',
      business: 'bg-orange-900/30 text-orange-400',
    };
    return map[plan ?? ''] ?? 'bg-gray-700 text-gray-400';
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  toggleRssi(user: AdminUser) {
    this.http
      .patch<{
        id: number;
        is_rssi_consultant: boolean;
      }>(`/api/v1/admin/users/${user.id}/rssi`, {}, { headers: this.auth.headers() })
      .subscribe({
        next: res => {
          this.users.update(list =>
            list.map(u =>
              u.id === res.id ? { ...u, is_rssi_consultant: res.is_rssi_consultant } : u
            )
          );
        },
      });
  }
}
