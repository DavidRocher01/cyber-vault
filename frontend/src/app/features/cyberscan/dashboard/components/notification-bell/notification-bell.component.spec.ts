/**
 * NotificationBellComponent — tests des methodes (logique extraite du dashboard).
 */
import { describe, it, expect, vi } from 'vitest';
import { signal } from '@angular/core';
import { of } from 'rxjs';
import { NotificationBellComponent } from './notification-bell.component';

function make(): NotificationBellComponent {
  const comp = Object.create(NotificationBellComponent.prototype) as NotificationBellComponent;
  (comp as any).notifications = signal([]);
  (comp as any).unreadCount = signal(0);
  (comp as any).showPanel = signal(false);
  return comp;
}

describe('NotificationBellComponent — formatDate()', () => {
  it('retourne "—" pour null', () => expect(make().formatDate(null)).toBe('—'));
  it("inclut l'heure dans le format", () => {
    const result = make().formatDate('2024-06-01T12:00:00Z');
    expect(result).toMatch(/\d+:\d+/);
  });
});

describe('NotificationBellComponent — togglePanel()', () => {
  it('inverse showPanel et stoppe la propagation', () => {
    const c = make();
    const event = { stopPropagation: vi.fn() } as any;
    c.togglePanel(event);
    expect(c.showPanel()).toBe(true);
    expect(event.stopPropagation).toHaveBeenCalled();
  });
});

describe('NotificationBellComponent — load()', () => {
  it('met à jour notifications et unreadCount', () => {
    const c = make();
    (c as any).notifApi = {
      getNotifications: vi.fn().mockReturnValue(of({ items: [{ id: 1 }], unread_count: 3 })),
    };
    c.load();
    expect(c.notifications()).toHaveLength(1);
    expect(c.unreadCount()).toBe(3);
  });
});

describe('NotificationBellComponent — handleClick()', () => {
  it('marque comme lue si non lue et décrémente le compteur', () => {
    const c = make();
    const notif = { id: 1, read: false, link: null } as any;
    (c as any).notifications = signal([notif]);
    (c as any).unreadCount = signal(2);
    (c as any).notifApi = {
      markNotificationRead: vi.fn().mockReturnValue(of({ id: 1, read: true })),
    };
    c.handleClick(notif);
    expect((c as any).notifApi.markNotificationRead).toHaveBeenCalledWith(1);
    expect(c.unreadCount()).toBe(1);
    expect(c.notifications()[0].read).toBe(true);
  });
  it('ne marque pas si déjà lue mais navigue si lien', () => {
    const c = make();
    const notif = { id: 1, read: true, link: '/cible' } as any;
    (c as any).notifApi = { markNotificationRead: vi.fn() };
    (c as any).router = { navigateByUrl: vi.fn() };
    (c as any).showPanel = signal(true);
    c.handleClick(notif);
    expect((c as any).notifApi.markNotificationRead).not.toHaveBeenCalled();
    expect((c as any).router.navigateByUrl).toHaveBeenCalledWith('/cible');
    expect(c.showPanel()).toBe(false);
  });
});

describe('NotificationBellComponent — markAllRead()', () => {
  it('passe toutes les notifs en lues et remet le compteur à 0', () => {
    const c = make();
    (c as any).notifications = signal([
      { id: 1, read: false },
      { id: 2, read: false },
    ]);
    (c as any).unreadCount = signal(2);
    (c as any).notifApi = {
      markAllNotificationsRead: vi.fn().mockReturnValue(of({})),
    };
    c.markAllRead();
    expect(c.notifications().every(n => n.read)).toBe(true);
    expect(c.unreadCount()).toBe(0);
  });
});

describe('NotificationBellComponent — dismiss()', () => {
  it('retire la notif et décrémente si elle était non lue', () => {
    const c = make();
    (c as any).notifications = signal([{ id: 1, read: false }]);
    (c as any).unreadCount = signal(1);
    (c as any).notifApi = {
      deleteNotification: vi.fn().mockReturnValue(of({})),
    };
    const event = { stopPropagation: vi.fn() } as any;
    c.dismiss(event, 1);
    expect(event.stopPropagation).toHaveBeenCalled();
    expect(c.notifications()).toHaveLength(0);
    expect(c.unreadCount()).toBe(0);
  });
  it('ne décrémente pas si la notif était déjà lue', () => {
    const c = make();
    (c as any).notifications = signal([{ id: 1, read: true }]);
    (c as any).unreadCount = signal(0);
    (c as any).notifApi = {
      deleteNotification: vi.fn().mockReturnValue(of({})),
    };
    c.dismiss({ stopPropagation: vi.fn() } as any, 1);
    expect(c.notifications()).toHaveLength(0);
    expect(c.unreadCount()).toBe(0);
  });
});
