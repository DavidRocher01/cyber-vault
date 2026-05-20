import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { NgClass } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Title, Meta } from '@angular/platform-browser';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { BookingService, Slot } from './booking.service';
import { NEED_OPTIONS } from '../contact/contact.component';

type Step = 'calendar' | 'form' | 'confirmed';

@Component({
  standalone: true,
  selector: 'app-booking',
  imports: [NgClass, RouterLink, ReactiveFormsModule, MatIconModule, NavButtonsComponent],
  templateUrl: './booking.component.html',
})
export class BookingComponent implements OnInit {
  private titleService = inject(Title);
  private meta = inject(Meta);
  private route = inject(ActivatedRoute);
  private fb = inject(FormBuilder);
  readonly bookingSvc = inject(BookingService);

  readonly needOptions = NEED_OPTIONS;

  // ── Calendar state ─────────────────────────────────────────────────────────
  today = new Date();
  currentYear = signal(this.today.getFullYear());
  currentMonth = signal(this.today.getMonth()); // 0-indexed

  slots = signal<Slot[]>([]);
  loadingSlots = signal(false);
  selectedDay = signal<string | null>(null);
  selectedSlot = signal<Slot | null>(null);

  step = signal<Step>('calendar');
  submitting = signal(false);
  apiError = signal('');
  confirmedMessage = signal('');
  cancelMode = signal(false);
  cancelToken = signal('');
  cancelResult = signal('');
  cancelLoading = signal(false);

  // ── Computed ────────────────────────────────────────────────────────────────
  monthLabel = computed(() => {
    return new Date(this.currentYear(), this.currentMonth(), 1)
      .toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  });

  calendarDays = computed<Array<string | null>>(() => {
    const y = this.currentYear();
    const m = this.currentMonth();
    const first = new Date(y, m, 1);
    const last = new Date(y, m + 1, 0);
    // Monday = 0 padding
    const pad = (first.getDay() + 6) % 7;
    const days: Array<string | null> = Array(pad).fill(null);
    for (let d = 1; d <= last.getDate(); d++) {
      days.push(`${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`);
    }
    return days;
  });

  availableDays = computed<Set<string>>(() => {
    return new Set(
      this.slots()
        .filter(s => !s.is_booked)
        .map(s => s.date)
    );
  });

  daySlotsSelected = computed<Slot[]>(() => {
    const day = this.selectedDay();
    if (!day) return [];
    return this.slots().filter(s => s.date === day && !s.is_booked);
  });

  isPast(dateStr: string): boolean {
    return dateStr < this.today.toISOString().slice(0, 10);
  }

  // ── Form ───────────────────────────────────────────────────────────────────
  form = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    email: ['', [Validators.required, Validators.email]],
    phone: [''],
    need_type: ['', Validators.required],
    message: [''],
  });

  get f() { return this.form.controls; }

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  ngOnInit() {
    this.titleService.setTitle('Réserver un audit cybersécurité | CyberScan');
    this.meta.updateTag({ name: 'description', content: 'Réservez un créneau pour un audit cybersécurité PME. Calendrier en ligne, confirmation immédiate.' });

    // Cancel flow via URL token
    const token = this.route.snapshot.queryParamMap.get('token');
    if (this.route.snapshot.url.some(s => s.path === 'annuler') && token) {
      this.cancelMode.set(true);
      this.cancelToken.set(token);
      this.cancelLoading.set(true);
      this.bookingSvc.cancel(token).subscribe({
        next: r => { this.cancelResult.set(r.message); this.cancelLoading.set(false); },
        error: () => { this.cancelResult.set('Réservation introuvable ou déjà annulée.'); this.cancelLoading.set(false); },
      });
      return;
    }

    // Pre-fill from scan-detail CTA (?domain=...&need_type=...)
    const domain   = this.route.snapshot.queryParamMap.get('domain');
    const needType = this.route.snapshot.queryParamMap.get('need_type');
    if (domain) {
      this.form.patchValue({
        message: `Suite au scan automatisé de ${domain}, je souhaite bénéficier d'un Audit Flash humain.`,
      });
    }
    if (needType) {
      this.form.patchValue({ need_type: needType });
    }

    this.loadMonth();
  }

  loadMonth() {
    const month = `${this.currentYear()}-${String(this.currentMonth() + 1).padStart(2, '0')}`;
    this.loadingSlots.set(true);
    this.selectedDay.set(null);
    this.selectedSlot.set(null);
    this.bookingSvc.getSlots(month).subscribe({
      next: s => { this.slots.set(s); this.loadingSlots.set(false); },
      error: () => { this.slots.set([]); this.loadingSlots.set(false); },
    });
  }

  prevMonth() {
    if (this.currentMonth() === 0) {
      this.currentMonth.set(11);
      this.currentYear.update(y => y - 1);
    } else {
      this.currentMonth.update(m => m - 1);
    }
    this.loadMonth();
  }

  nextMonth() {
    if (this.currentMonth() === 11) {
      this.currentMonth.set(0);
      this.currentYear.update(y => y + 1);
    } else {
      this.currentMonth.update(m => m + 1);
    }
    this.loadMonth();
  }

  canPrevMonth(): boolean {
    const y = this.currentYear();
    const m = this.currentMonth();
    return y > this.today.getFullYear() || (y === this.today.getFullYear() && m > this.today.getMonth());
  }

  selectDay(day: string) {
    if (this.isPast(day) || !this.availableDays().has(day)) return;
    this.selectedDay.set(day);
    this.selectedSlot.set(null);
  }

  selectSlot(slot: Slot) {
    this.selectedSlot.set(slot);
    this.step.set('form');
  }

  backToCalendar() {
    this.step.set('calendar');
    this.apiError.set('');
  }

  formatDayFr(dateStr: string): string {
    const months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
      'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
    const [y, m, d] = dateStr.split('-');
    return `${parseInt(d)} ${months[parseInt(m) - 1]} ${y}`;
  }

  getDayNum(dateStr: string): number {
    return parseInt(dateStr.split('-')[2]);
  }

  submit() {
    if (this.form.invalid || this.submitting() || !this.selectedSlot()) return;
    this.submitting.set(true);
    this.apiError.set('');
    const slot = this.selectedSlot()!;
    const { name, email, phone, need_type, message } = this.form.value;
    this.bookingSvc.book({
      slot_id: slot.id,
      name: name!,
      email: email!,
      phone: phone || undefined,
      need_type: need_type!,
      message: message || undefined,
    }).subscribe({
      next: r => {
        this.confirmedMessage.set(r.message);
        this.step.set('confirmed');
        this.submitting.set(false);
      },
      error: err => {
        this.apiError.set(err?.error?.detail ?? 'Une erreur est survenue. Réessayez.');
        this.submitting.set(false);
      },
    });
  }
}
