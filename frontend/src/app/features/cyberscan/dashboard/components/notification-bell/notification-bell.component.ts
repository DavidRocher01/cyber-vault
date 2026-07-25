import {
  Component,
  DestroyRef,
  ElementRef,
  HostListener,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { interval } from 'rxjs';
import { AppNotification } from '../../../services/cyberscan.service';
import { NotificationApiService } from '../../../services/notification-api.service';
import { formatFrDate } from '../../../../../shared/date-utils';

/**
 * Cloche de notifications de la navbar dashboard.
 *
 * Composant autonome : il interroge lui-meme l'API (polling 30 s), gere son
 * propre panneau ouvert/ferme (fermeture au clic exterieur) et n'expose aucun
 * @Input/@Output — il etait auparavant fondu dans DashboardComponent.
 */
@Component({
  standalone: true,
  selector: 'app-notification-bell',
  imports: [MatButtonModule, MatIconModule],
  template: `
    <div class="relative notif-panel-anchor">
      <button
        type="button"
        mat-icon-button
        (click)="togglePanel($event)"
        class="relative !text-gray-400 hover:!text-white"
      >
        <mat-icon>notifications</mat-icon>
        @if (unreadCount() > 0) {
          <span
            class="absolute top-1.5 right-1.5 w-3.5 h-3.5 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center leading-none"
          >
            {{ unreadCount() > 9 ? '9+' : unreadCount() }}
          </span>
        }
      </button>
      @if (showPanel()) {
        <div
          class="absolute right-0 top-full mt-2 w-80 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden"
          (click)="$event.stopPropagation()"
        >
          <div class="flex items-center justify-between px-4 py-3 border-b border-gray-700">
            <span class="font-semibold text-sm">Notifications</span>
            @if (unreadCount() > 0) {
              <button
                type="button"
                mat-button
                class="!text-xs !text-cyan-400 !px-0"
                (click)="markAllRead()"
              >
                Tout lire
              </button>
            }
          </div>
          @if (notifications().length === 0) {
            <div class="py-8 text-center text-gray-500 text-sm">
              <mat-icon class="!text-3xl mb-2 text-gray-600">notifications_none</mat-icon>
              <p>Aucune notification</p>
            </div>
          } @else {
            <div class="max-h-96 overflow-y-auto">
              @for (notif of notifications(); track notif.id) {
                <div
                  class="flex items-start gap-3 px-4 py-3 border-b border-gray-700/50 cursor-pointer transition-colors"
                  [class]="notif.read ? 'hover:bg-gray-700/40' : 'bg-gray-700/60 hover:bg-gray-700'"
                  (click)="handleClick(notif)"
                >
                  <div class="flex-1 min-w-0">
                    <p
                      class="text-sm font-medium leading-snug truncate"
                      [class]="notif.read ? 'text-gray-300' : 'text-white'"
                    >
                      {{ notif.title }}
                    </p>
                    @if (notif.body) {
                      <p class="text-xs text-gray-500 mt-0.5 truncate">{{ notif.body }}</p>
                    }
                    <p class="text-[10px] text-gray-600 mt-1">
                      {{ formatDate(notif.created_at) }}
                    </p>
                  </div>
                  <button
                    type="button"
                    mat-icon-button
                    class="!w-6 !h-6 !text-gray-500 hover:!text-gray-300 flex-shrink-0 !min-w-0"
                    (click)="dismiss($event, notif.id)"
                  >
                    <mat-icon class="!text-sm">close</mat-icon>
                  </button>
                </div>
              }
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class NotificationBellComponent implements OnInit {
  private notifApi = inject(NotificationApiService);
  private router = inject(Router);
  private el = inject(ElementRef);
  private destroyRef = inject(DestroyRef);

  notifications = signal<AppNotification[]>([]);
  unreadCount = signal(0);
  showPanel = signal(false);

  ngOnInit() {
    this.load();
    interval(30000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.load());
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    if (
      this.showPanel() &&
      !this.el.nativeElement.querySelector('.notif-panel-anchor')?.contains(event.target)
    ) {
      this.showPanel.set(false);
    }
  }

  load() {
    this.notifApi.getNotifications().subscribe({
      next: data => {
        this.notifications.set(data.items);
        this.unreadCount.set(data.unread_count);
      },
      error: () => {},
    });
  }

  togglePanel(event: MouseEvent) {
    event.stopPropagation();
    this.showPanel.update(v => !v);
  }

  handleClick(notif: AppNotification) {
    if (!notif.read) {
      this.notifApi.markNotificationRead(notif.id).subscribe({
        next: updated => {
          this.notifications.update(list => list.map(n => (n.id === notif.id ? updated : n)));
          this.unreadCount.update(c => Math.max(0, c - 1));
        },
        error: () => {},
      });
    }
    if (notif.link) {
      this.router.navigateByUrl(notif.link);
      this.showPanel.set(false);
    }
  }

  markAllRead() {
    this.notifApi.markAllNotificationsRead().subscribe({
      next: () => {
        this.notifications.update(list => list.map(n => ({ ...n, read: true })));
        this.unreadCount.set(0);
      },
      error: () => {},
    });
  }

  dismiss(event: MouseEvent, id: number) {
    event.stopPropagation();
    this.notifApi.deleteNotification(id).subscribe({
      next: () => {
        const notif = this.notifications().find(n => n.id === id);
        this.notifications.update(list => list.filter(n => n.id !== id));
        if (notif && !notif.read) this.unreadCount.update(c => Math.max(0, c - 1));
      },
      error: () => {},
    });
  }

  formatDate(d: string | null): string {
    return formatFrDate(d, 'datetime');
  }
}
