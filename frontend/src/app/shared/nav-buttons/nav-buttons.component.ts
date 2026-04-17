import { Component, inject } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NavHistoryService } from '../../core/services/nav-history.service';

@Component({
    standalone: true,
    selector: 'app-nav-buttons',
    imports: [MatIconModule, MatTooltipModule],
    template: `
    <div style="display:flex;align-items:center;gap:2px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:3px">
      <button type="button"
              (click)="nav.back()"
              [disabled]="!nav.canGoBack()"
              matTooltip="Page précédente"
              [style.opacity]="nav.canGoBack() ? '1' : '0.35'"
              [style.cursor]="nav.canGoBack() ? 'pointer' : 'not-allowed'"
              style="width:32px;height:32px;border-radius:8px;border:none;background:transparent;display:flex;align-items:center;justify-content:center;color:white;transition:background 0.15s"
              (mouseenter)="nav.canGoBack() && setHover('back', true)"
              (mouseleave)="setHover('back', false)"
              [style.background]="hoverBack && nav.canGoBack() ? 'rgba(6,182,212,0.25)' : 'transparent'">
        <mat-icon style="font-size:18px;width:18px;height:18px">arrow_back</mat-icon>
      </button>
      <button type="button"
              (click)="nav.forward()"
              [disabled]="!nav.canGoForward()"
              matTooltip="Page suivante"
              [style.opacity]="nav.canGoForward() ? '1' : '0.35'"
              [style.cursor]="nav.canGoForward() ? 'pointer' : 'not-allowed'"
              style="width:32px;height:32px;border-radius:8px;border:none;background:transparent;display:flex;align-items:center;justify-content:center;color:white;transition:background 0.15s"
              (mouseenter)="nav.canGoForward() && setHover('fwd', true)"
              (mouseleave)="setHover('fwd', false)"
              [style.background]="hoverFwd && nav.canGoForward() ? 'rgba(6,182,212,0.25)' : 'transparent'">
        <mat-icon style="font-size:18px;width:18px;height:18px">arrow_forward</mat-icon>
      </button>
    </div>
  `
})
export class NavButtonsComponent {
  readonly nav = inject(NavHistoryService);
  hoverBack = false;
  hoverFwd  = false;

  setHover(btn: 'back' | 'fwd', val: boolean) {
    if (btn === 'back') this.hoverBack = val;
    else this.hoverFwd = val;
  }
}
