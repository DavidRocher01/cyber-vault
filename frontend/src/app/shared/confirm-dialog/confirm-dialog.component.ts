import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirm: string;
  danger?: boolean;
}

@Component({
    standalone: true,
    selector: 'app-confirm-dialog',
    imports: [MatDialogModule, MatButtonModule, MatIconModule],
    template: `
    <div class="bg-gray-900 rounded-2xl overflow-hidden w-full" style="min-width:380px;max-width:440px">

      <!-- Header -->
      <div class="px-6 pt-6 pb-4 flex items-start gap-4">
        <div class="flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center"
             [class]="data.danger ? 'bg-red-500/15 border border-red-500/30' : 'bg-cyan-500/15 border border-cyan-500/30'">
          <mat-icon class="!text-[1.3rem] !w-[1.3rem] !h-[1.3rem]"
                    [class]="data.danger ? 'text-red-400' : 'text-cyan-400'">
            {{ data.danger ? 'delete_forever' : 'help_outline' }}
          </mat-icon>
        </div>
        <div class="flex-1 min-w-0">
          <h2 class="text-white font-bold text-lg leading-tight">{{ data.title }}</h2>
          <p class="text-gray-400 text-sm mt-1 leading-relaxed">{{ data.message }}</p>
        </div>
      </div>

      <!-- Danger notice -->
      @if (data.danger) {
        <div class="mx-6 mb-4 flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2.5">
          <mat-icon class="text-red-400 !text-[1rem] !w-[1rem] !h-[1rem] flex-shrink-0">warning</mat-icon>
          <p class="text-red-300 text-xs">Cette action est irréversible.</p>
        </div>
      }

      <!-- Actions -->
      <div class="px-6 pb-6 flex items-center justify-end gap-3">
        <button type="button" (click)="ref.close(false)"
                class="px-4 py-2 rounded-xl text-sm font-semibold text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 hover:bg-gray-800 transition-all">
          Annuler
        </button>
        <button type="button" (click)="ref.close(true)"
                class="px-5 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                [class]="data.danger
                  ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/30'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-900/30'">
          <mat-icon class="!text-[1rem] !w-[1rem] !h-[1rem]">
            {{ data.danger ? 'delete' : 'check' }}
          </mat-icon>
          {{ data.confirm }}
        </button>
      </div>

    </div>
  `
})
export class ConfirmDialogComponent {
  data = inject<ConfirmDialogData>(MAT_DIALOG_DATA);
  ref = inject(MatDialogRef<ConfirmDialogComponent>);
}
