import { Component, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { Slot } from '../booking/booking.service';

interface AdminBooking {
  id: number;
  slot_id: number;
  name: string;
  email: string;
  phone: string | null;
  need_type: string;
  message: string | null;
  status: string;
  created_at: string;
}

@Component({
  standalone: true,
  selector: 'app-booking-admin',
  imports: [ReactiveFormsModule, MatIconModule, NavButtonsComponent],
  templateUrl: './booking-admin.component.html',
})
export class BookingAdminComponent {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  adminKey = signal('');
  authenticated = signal(false);
  authError = signal('');

  slots = signal<Slot[]>([]);
  bookings = signal<AdminBooking[]>([]);
  currentMonth = signal(new Date().toISOString().slice(0, 7)); // YYYY-MM
  loading = signal(false);
  addError = signal('');
  addSuccess = signal('');

  keyForm = this.fb.group({ key: ['', Validators.required] });

  slotForm = this.fb.group({
    date: ['', Validators.required],
    time: ['', Validators.required],
    duration_minutes: [30],
    label: ['Appel découverte'],
  });

  private headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Admin-Key': this.adminKey() });
  }

  login() {
    const key = this.keyForm.value.key ?? '';
    this.authError.set('');
    this.http.get<Slot[]>(`/api/v1/bookings/admin/slots`, { headers: new HttpHeaders({ 'X-Admin-Key': key }) }).subscribe({
      next: () => { this.adminKey.set(key); this.authenticated.set(true); this.loadData(); },
      error: () => this.authError.set('Clé admin incorrecte.'),
    });
  }

  loadData() {
    this.loading.set(true);
    const month = this.currentMonth();
    this.http.get<Slot[]>(`/api/v1/bookings/admin/slots?month=${month}`, { headers: this.headers() }).subscribe({
      next: s => this.slots.set(s),
    });
    this.http.get<AdminBooking[]>(`/api/v1/bookings/admin/bookings`, { headers: this.headers() }).subscribe({
      next: b => { this.bookings.set(b); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  addSlot() {
    if (this.slotForm.invalid) return;
    const { date, time, duration_minutes, label } = this.slotForm.value;
    this.addError.set('');
    this.addSuccess.set('');
    this.http.post<Slot[]>('/api/v1/bookings/admin/slots',
      { slots: [{ date, time, duration_minutes, label }] },
      { headers: this.headers() }
    ).subscribe({
      next: () => { this.addSuccess.set('Créneau ajouté !'); this.loadData(); },
      error: err => this.addError.set(err?.error?.detail ?? 'Erreur'),
    });
  }

  deleteSlot(id: number) {
    this.http.delete(`/api/v1/bookings/admin/slots/${id}`, { headers: this.headers() }).subscribe({
      next: () => this.loadData(),
    });
  }

  cancelBooking(id: number) {
    this.http.patch(`/api/v1/bookings/admin/bookings/${id}/cancel`, {}, { headers: this.headers() }).subscribe({
      next: () => this.loadData(),
    });
  }

  prevMonth() {
    const [y, m] = this.currentMonth().split('-').map(Number);
    const d = new Date(y, m - 2, 1);
    this.currentMonth.set(d.toISOString().slice(0, 7));
    this.loadData();
  }

  nextMonth() {
    const [y, m] = this.currentMonth().split('-').map(Number);
    const d = new Date(y, m, 1);
    this.currentMonth.set(d.toISOString().slice(0, 7));
    this.loadData();
  }

  formatMonthLabel(): string {
    const [y, m] = this.currentMonth().split('-').map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  }

  monthBookings = computed(() => {
    const month = this.currentMonth();
    const slotIds = new Set(this.slots().map(s => s.id));
    return this.bookings().filter(b => slotIds.has(b.slot_id) && b.status === 'confirmed');
  });

  slotDateLabel(slotId: number): string {
    const s = this.slots().find(s => s.id === slotId);
    return s ? `${s.date} ${s.time}` : '—';
  }

  needLabel(nt: string): string {
    const map: Record<string, string> = {
      'audit-flash': 'Flash', 'audit-app': 'App-Check',
      'pentest': 'Pentest', 'abonnement': 'Abonnement', 'autre': 'Autre',
    };
    return map[nt] ?? nt;
  }
}
