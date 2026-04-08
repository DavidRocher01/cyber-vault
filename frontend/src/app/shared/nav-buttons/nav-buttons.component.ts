import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NavHistoryService } from '../../core/services/nav-history.service';

@Component({
  selector: 'app-nav-buttons',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatTooltipModule],
  template: `
    <div class="flex items-center gap-1 bg-gray-800/60 border border-gray-700 rounded-xl px-1 py-1">
      <button type="button"
              (click)="nav.back()"
              [disabled]="!nav.canGoBack"
              matTooltip="Page précédente"
              class="w-8 h-8 rounded-lg flex items-center justify-center transition-all"
              [class.text-white]="nav.canGoBack"
              [class.bg-gray-700]="nav.canGoBack"
              [class.hover:bg-cyan-600]="nav.canGoBack"
              [class.text-gray-600]="!nav.canGoBack"
              [class.cursor-not-allowed]="!nav.canGoBack"
              [class.opacity-40]="!nav.canGoBack">
        <mat-icon class="!text-[1rem] !w-[1rem] !h-[1rem]">arrow_back</mat-icon>
      </button>
      <button type="button"
              (click)="nav.forward()"
              [disabled]="!nav.canGoForward"
              matTooltip="Page suivante"
              class="w-8 h-8 rounded-lg flex items-center justify-center transition-all"
              [class.text-white]="nav.canGoForward"
              [class.bg-gray-700]="nav.canGoForward"
              [class.hover:bg-cyan-600]="nav.canGoForward"
              [class.text-gray-600]="!nav.canGoForward"
              [class.cursor-not-allowed]="!nav.canGoForward"
              [class.opacity-40]="!nav.canGoForward">
        <mat-icon class="!text-[1rem] !w-[1rem] !h-[1rem]">arrow_forward</mat-icon>
      </button>
    </div>
  `,
})
export class NavButtonsComponent {
  readonly nav = inject(NavHistoryService);
}
