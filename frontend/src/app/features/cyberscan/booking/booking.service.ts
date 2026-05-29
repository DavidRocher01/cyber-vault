import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Slot {
  id: number;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
  duration_minutes: number;
  label: string;
  is_booked: boolean;
}

export interface BookingPayload {
  slot_id: number;
  name: string;
  email: string;
  phone?: string;
  need_type: string;
  message?: string;
}

export interface BookingConfirm {
  message: string;
  booking_id: number;
}

@Injectable({ providedIn: 'root' })
export class BookingService {
  http = inject(HttpClient);

  getSlots(month: string): Observable<Slot[]> {
    return this.http.get<Slot[]>(`/api/v1/bookings/slots?month=${month}`);
  }

  book(payload: BookingPayload): Observable<BookingConfirm> {
    return this.http.post<BookingConfirm>('/api/v1/bookings', payload);
  }

  cancel(token: string): Observable<{ message: string }> {
    return this.http.get<{ message: string }>(`/api/v1/bookings/cancel?token=${token}`);
  }
}
