import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { AppNotification, NotificationList } from './cyberscan.service';

const API = '/api/v1';

/** Domaine notifications extrait de CyberscanService. */
@Injectable({ providedIn: 'root' })
export class NotificationApiService {
  private http = inject(HttpClient);

  getNotifications(): Observable<NotificationList> {
    return this.http.get<NotificationList>(`${API}/notifications`);
  }

  markNotificationRead(id: number): Observable<AppNotification> {
    return this.http.post<AppNotification>(`${API}/notifications/${id}/read`, {});
  }

  markAllNotificationsRead(): Observable<void> {
    return this.http.post<void>(`${API}/notifications/read-all`, {});
  }

  deleteNotification(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/notifications/${id}`);
  }
}
