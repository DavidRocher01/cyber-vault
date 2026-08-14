import { Component, inject } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

import { NotificationsService, type TonNotification } from '../../core/notifications.service';

const ICONE: Record<TonNotification, string> = {
  succes: 'check_circle',
  erreur: 'error',
  avertissement: 'warning',
};

const TEINTE: Record<TonNotification, string> = {
  succes: 'border-emerald-500/60 text-emerald-300',
  erreur: 'border-red-500/60 text-red-300',
  avertissement: 'border-amber-500/60 text-amber-300',
};

/**
 * Hote d'affichage des notifications ephemeres.
 *
 * Il vit hors du `@if (!loading)` d'`AppComponent` : le chargeur reste affiche
 * 1,8 s, et l'intercepteur peut signaler un 429 pendant ce temps. A l'interieur,
 * le message serait perdu.
 */
@Component({
  standalone: true,
  selector: 'app-notifications',
  imports: [MatIconModule],
  template: `
    <div
      class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[60] flex flex-col items-center gap-2 px-4 pointer-events-none"
      role="status"
      aria-live="polite"
    >
      @for (n of service.actives(); track n.id) {
        <div
          class="apparait pointer-events-auto flex items-center gap-3 max-w-md rounded-lg border bg-gray-900/95 backdrop-blur-sm px-4 py-3 shadow-lg shadow-black/40"
          [class]="teinte(n.ton)"
        >
          <mat-icon class="flex-shrink-0 !text-xl !w-5 !h-5">{{ icone(n.ton) }}</mat-icon>
          <span class="text-sm text-gray-100">{{ n.texte }}</span>
          <button
            type="button"
            class="flex-shrink-0 text-gray-500 hover:text-gray-200 transition-colors"
            [attr.aria-label]="'Fermer : ' + n.texte"
            (click)="service.fermer(n.id)"
          >
            <mat-icon class="!text-lg !w-4 !h-4">close</mat-icon>
          </button>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .apparait {
        animation: monte 160ms ease-out;
      }

      @keyframes monte {
        from {
          opacity: 0;
          transform: translateY(0.5rem);
        }
        to {
          opacity: 1;
          transform: none;
        }
      }

      @media (prefers-reduced-motion: reduce) {
        .apparait {
          animation: none;
        }
      }
    `,
  ],
})
export class NotificationsComponent {
  readonly service = inject(NotificationsService);

  icone(ton: TonNotification): string {
    return ICONE[ton];
  }

  teinte(ton: TonNotification): string {
    return TEINTE[ton];
  }
}
