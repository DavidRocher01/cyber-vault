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
    <div class="flex items-center gap-1">
      <button type="button"
              (click)="nav.back()"
              [disabled]="!nav.canGoBack"
              matTooltip="Page précédente"
              class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
              [class.text-gray-400]="nav.canGoBack"
              [class.hover:bg-gray-800]="nav.canGoBack"
              [class.hover:text-white]="nav.canGoBack"
              [class.text-gray-700]="!nav.canGoBack"
              [class.cursor-not-allowed]="!nav.canGoBack">
        <mat-icon class="!text-[1.1rem] !w-[1.1rem] !h-[1.1rem]">arrow_back</mat-icon>
      </button>
      <button type="button"
              (click)="nav.forward()"
              [disabled]="!nav.canGoForward"
              matTooltip="Page suivante"
              class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
              [class.text-gray-400]="nav.canGoForward"
              [class.hover:bg-gray-800]="nav.canGoForward"
              [class.hover:text-white]="nav.canGoForward"
              [class.text-gray-700]="!nav.canGoForward"
              [class.cursor-not-allowed]="!nav.canGoForward">
        <mat-icon class="!text-[1.1rem] !w-[1.1rem] !h-[1.1rem]">arrow_forward</mat-icon>
      </button>
    </div>
  `,
})
export class NavButtonsComponent {
  readonly nav = inject(NavHistoryService);
}
