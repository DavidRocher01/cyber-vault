import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { AdminAuthService } from '../admin-auth.service';

interface ContactMessage {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  need_type: string;
  site_url: string | null;
  message: string;
  status: string;
  created_at: string;
}

@Component({
  standalone: true,
  selector: 'app-admin-contacts',
  imports: [MatIconModule],
  templateUrl: './admin-contacts.component.html',
})
export class AdminContactsComponent implements OnInit {
  private http = inject(HttpClient);
  auth = inject(AdminAuthService);

  messages = signal<ContactMessage[]>([]);
  loading = signal(true);
  filter = signal<'all' | 'new' | 'handled' | 'archived'>('all');
  expanded = signal<number | null>(null);

  filtered = computed(() => {
    const f = this.filter();
    return f === 'all' ? this.messages() : this.messages().filter(m => m.status === f);
  });

  ngOnInit() { this.load(); }

  load() {
    this.http.get<ContactMessage[]>('/api/v1/contact/admin/messages', { headers: this.auth.headers() }).subscribe({
      next: m => { this.messages.set(m); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  updateStatus(id: number, status: string) {
    this.http.patch(`/api/v1/contact/admin/messages/${id}/status`, { status }, { headers: this.auth.headers() }).subscribe({
      next: () => this.messages.update(msgs => msgs.map(m => m.id === id ? { ...m, status } : m)),
    });
  }

  toggleExpand(id: number) {
    this.expanded.update(v => v === id ? null : id);
  }

  needLabel(nt: string): string {
    const map: Record<string, string> = {
      'audit-flash': 'Audit Flash', 'audit-app': 'App-Check',
      'pentest': 'Pentest', 'abonnement': 'Abonnement', 'autre': 'Autre',
    };
    return map[nt] ?? nt;
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
}
