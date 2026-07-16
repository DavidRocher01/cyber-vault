import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ReactiveFormsModule, FormGroup } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RssiAction } from '../../../services/rssi.service';

interface LabelOption {
  value: string;
  label: string;
}

@Component({
  standalone: true,
  selector: 'app-actions-table',
  imports: [ReactiveFormsModule, MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <div>
      <div class="flex flex-wrap items-center gap-3 mb-4">
        <h2 class="text-sm font-semibold text-gray-300 mr-auto">Plan d'actions</h2>
        <!-- Filtres -->
        <div class="w-36">
          <label class="block text-xs font-medium text-gray-400 mb-1.5">Statut</label>
          <div class="relative">
            <select
              aria-label="Statut"
              #selStatus
              (change)="statusFilterChange.emit(selStatus.value)"
              class="w-full rounded-xl bg-gray-800/60 border border-gray-700 pl-3 pr-9 py-2.5 text-sm text-white outline-none appearance-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
            >
              <option value="all" [selected]="statusFilter === 'all'">Tous</option>
              @for (s of actionStatuses; track s.value) {
                <option [value]="s.value" [selected]="statusFilter === s.value">
                  {{ s.label }}
                </option>
              }
            </select>
            <mat-icon
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 !text-[1.15rem] !w-[1.15rem] !h-[1.15rem] pointer-events-none"
              >expand_more</mat-icon
            >
          </div>
        </div>
        <div class="w-36">
          <label class="block text-xs font-medium text-gray-400 mb-1.5">Priorité</label>
          <div class="relative">
            <select
              aria-label="Priorité"
              #selPriority
              (change)="priorityFilterChange.emit(selPriority.value)"
              class="w-full rounded-xl bg-gray-800/60 border border-gray-700 pl-3 pr-9 py-2.5 text-sm text-white outline-none appearance-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
            >
              <option value="all" [selected]="priorityFilter === 'all'">Toutes</option>
              @for (p of actionPriorities; track p.value) {
                <option [value]="p.value" [selected]="priorityFilter === p.value">
                  {{ p.label }}
                </option>
              }
            </select>
            <mat-icon
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 !text-[1.15rem] !w-[1.15rem] !h-[1.15rem] pointer-events-none"
              >expand_more</mat-icon
            >
          </div>
        </div>
        <button
          type="button"
          mat-stroked-button
          (click)="exportCsv.emit()"
          [disabled]="exportingCsv"
          matTooltip="Exporter en CSV (compatible Excel)"
          class="!rounded-xl !border-gray-700 !text-gray-400 !text-sm"
        >
          @if (exportingCsv) {
            <mat-icon class="animate-spin">sync</mat-icon>
          } @else {
            <mat-icon>download</mat-icon>
          }
          CSV
        </button>
        <button
          type="button"
          mat-flat-button
          (click)="toggleAddForm.emit()"
          class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-sm"
        >
          <mat-icon>{{ showAddForm ? 'close' : 'add' }}</mat-icon>
          {{ showAddForm ? 'Annuler' : 'Nouvelle action' }}
        </button>
      </div>

      @if (showAddForm) {
        <form
          [formGroup]="addForm"
          (ngSubmit)="submitAdd()"
          class="bg-gray-900 border border-cyan-700/50 rounded-xl p-4 mb-4 grid grid-cols-1 md:grid-cols-3 gap-3"
        >
          <div class="md:col-span-2">
            <label class="block text-xs font-medium text-gray-400 mb-1.5"
              >Titre <span class="text-red-400">*</span></label
            >
            <input
              type="text"
              formControlName="title"
              placeholder="Mettre en place MFA…"
              class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-400 mb-1.5">Priorité</label>
            <div class="relative">
              <select
                aria-label="Priorité"
                formControlName="priority"
                class="w-full rounded-xl bg-gray-800/60 border border-gray-700 pl-3 pr-9 py-2.5 text-sm text-white outline-none appearance-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
              >
                @for (p of actionPriorities; track p.value) {
                  <option [value]="p.value">{{ p.label }}</option>
                }
              </select>
              <mat-icon
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 !text-[1.15rem] !w-[1.15rem] !h-[1.15rem] pointer-events-none"
                >expand_more</mat-icon
              >
            </div>
          </div>
          <div class="md:col-span-3">
            <label class="block text-xs font-medium text-gray-400 mb-1.5">Description</label>
            <textarea
              formControlName="description"
              rows="2"
              placeholder="Détails…"
              class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all resize-y focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
            ></textarea>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-400 mb-1.5">Catégorie</label>
            <div class="relative">
              <select
                aria-label="Catégorie"
                formControlName="category"
                class="w-full rounded-xl bg-gray-800/60 border border-gray-700 pl-3 pr-9 py-2.5 text-sm text-white outline-none appearance-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
              >
                <option value="">—</option>
                <option value="governance">Gouvernance</option>
                <option value="technical">Technique</option>
                <option value="training">Formation</option>
                <option value="compliance">Conformité</option>
              </select>
              <mat-icon
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 !text-[1.15rem] !w-[1.15rem] !h-[1.15rem] pointer-events-none"
                >expand_more</mat-icon
              >
            </div>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-400 mb-1.5">Responsable</label>
            <input
              type="text"
              formControlName="assigned_to"
              placeholder="ciso@client.com"
              class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-400 mb-1.5">Échéance</label>
            <input
              type="date"
              formControlName="due_date"
              title="Date d'échéance de l'action"
              class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white outline-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
            />
          </div>
          <div class="md:col-span-3 flex justify-end gap-2">
            <button
              type="button"
              mat-stroked-button
              (click)="toggleAddForm.emit()"
              class="!rounded-xl !border-gray-700 !text-gray-400 !text-sm"
            >
              Annuler
            </button>
            <button
              mat-flat-button
              type="submit"
              [disabled]="saving"
              class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-sm"
            >
              Créer
            </button>
          </div>
        </form>
      }

      @if (filteredActions.length === 0) {
        <div class="text-center py-12 text-gray-500 text-sm">
          @if (totalActions === 0) {
            Aucune action pour ce client
          } @else {
            Aucune action ne correspond aux filtres sélectionnés
          }
        </div>
      } @else {
        <div class="flex flex-col gap-3">
          @for (a of filteredActions; track a.id) {
            @if (editingActionId === a.id) {
              <form
                [formGroup]="editForm"
                (ngSubmit)="submitEdit(a.id)"
                class="bg-gray-900 border border-cyan-700/50 rounded-xl p-4 grid grid-cols-1 md:grid-cols-3 gap-3"
              >
                <div class="md:col-span-2">
                  <label class="block text-xs font-medium text-gray-400 mb-1.5"
                    >Titre <span class="text-red-400">*</span></label
                  >
                  <input
                    type="text"
                    formControlName="title"
                    placeholder="Titre de l'action"
                    class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-400 mb-1.5">Statut</label>
                  <div class="relative">
                    <select
                      aria-label="Statut"
                      formControlName="status"
                      class="w-full rounded-xl bg-gray-800/60 border border-gray-700 pl-3 pr-9 py-2.5 text-sm text-white outline-none appearance-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
                    >
                      @for (s of actionStatuses; track s.value) {
                        <option [value]="s.value">{{ s.label }}</option>
                      }
                    </select>
                    <mat-icon
                      class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 !text-[1.15rem] !w-[1.15rem] !h-[1.15rem] pointer-events-none"
                      >expand_more</mat-icon
                    >
                  </div>
                </div>
                <div class="md:col-span-3">
                  <label class="block text-xs font-medium text-gray-400 mb-1.5">Description</label>
                  <textarea
                    formControlName="description"
                    rows="2"
                    placeholder="Détails de l'action…"
                    class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all resize-y focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
                  ></textarea>
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-400 mb-1.5">Catégorie</label>
                  <div class="relative">
                    <select
                      aria-label="Catégorie"
                      formControlName="category"
                      class="w-full rounded-xl bg-gray-800/60 border border-gray-700 pl-3 pr-9 py-2.5 text-sm text-white outline-none appearance-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
                    >
                      <option value="">—</option>
                      <option value="governance">Gouvernance</option>
                      <option value="technical">Technique</option>
                      <option value="training">Formation</option>
                      <option value="compliance">Conformité</option>
                    </select>
                    <mat-icon
                      class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 !text-[1.15rem] !w-[1.15rem] !h-[1.15rem] pointer-events-none"
                      >expand_more</mat-icon
                    >
                  </div>
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-400 mb-1.5">Priorité</label>
                  <div class="relative">
                    <select
                      aria-label="Priorité"
                      formControlName="priority"
                      class="w-full rounded-xl bg-gray-800/60 border border-gray-700 pl-3 pr-9 py-2.5 text-sm text-white outline-none appearance-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
                    >
                      @for (p of actionPriorities; track p.value) {
                        <option [value]="p.value">{{ p.label }}</option>
                      }
                    </select>
                    <mat-icon
                      class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 !text-[1.15rem] !w-[1.15rem] !h-[1.15rem] pointer-events-none"
                      >expand_more</mat-icon
                    >
                  </div>
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-400 mb-1.5">Responsable</label>
                  <input
                    type="text"
                    formControlName="assigned_to"
                    placeholder="ciso@client.com"
                    class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-400 mb-1.5">Échéance</label>
                  <input
                    type="date"
                    formControlName="due_date"
                    title="Date d'échéance de l'action"
                    class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white outline-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
                  />
                </div>
                <div class="md:col-span-3 flex justify-end gap-2">
                  <button
                    type="button"
                    mat-stroked-button
                    (click)="cancelEdit.emit()"
                    class="!rounded-xl !border-gray-700 !text-gray-400 !text-sm"
                  >
                    Annuler
                  </button>
                  <button
                    mat-flat-button
                    type="submit"
                    class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-sm"
                  >
                    Enregistrer
                  </button>
                </div>
              </form>
            } @else {
              <div
                class="bg-gray-900 border border-gray-800 rounded-xl p-4"
                [class.opacity-60]="a.status === 'done' || a.status === 'cancelled'"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap mb-1">
                      <span
                        class="font-semibold text-white"
                        [class]="a.status === 'done' ? 'line-through text-gray-400' : ''"
                      >
                        {{ a.title }}
                      </span>
                      <span
                        class="text-xs px-1.5 py-0.5 rounded-full border font-semibold"
                        [class]="priorityClass(a.priority)"
                      >
                        {{
                          a.priority === 'critical'
                            ? 'Critique'
                            : a.priority === 'high'
                              ? 'Haute'
                              : a.priority === 'medium'
                                ? 'Moyenne'
                                : 'Basse'
                        }}
                      </span>
                      <span
                        class="text-xs px-1.5 py-0.5 rounded-full border"
                        [class]="actionStatusClass(a.status)"
                      >
                        {{ actionStatusLabel(a.status) }}
                      </span>
                      @if (a.category) {
                        <span
                          class="text-xs px-1.5 py-0.5 rounded bg-gray-700/50 text-gray-400 border border-gray-600/30"
                        >
                          {{ a.category }}
                        </span>
                      }
                    </div>
                    @if (a.description) {
                      <p class="text-xs text-gray-400">{{ a.description }}</p>
                    }
                    <div class="flex gap-4 mt-1.5 text-xs text-gray-500 flex-wrap">
                      @if (a.assigned_to) {
                        <span>
                          <mat-icon
                            style="font-size: 12px; height: 12px; width: 12px"
                            class="align-middle"
                            >person</mat-icon
                          >
                          {{ a.assigned_to }}
                        </span>
                      }
                      @if (a.due_date) {
                        <span
                          [class]="
                            a.due_date < today && a.status !== 'done' && a.status !== 'cancelled'
                              ? 'text-red-400'
                              : ''
                          "
                        >
                          <mat-icon
                            style="font-size: 12px; height: 12px; width: 12px"
                            class="align-middle"
                            >event</mat-icon
                          >
                          {{ formatDate(a.due_date) }}
                        </span>
                      }
                    </div>
                  </div>
                  <div class="flex gap-1 shrink-0">
                    <button
                      type="button"
                      mat-icon-button
                      (click)="startEdit.emit(a)"
                      matTooltip="Modifier"
                    >
                      <mat-icon style="font-size: 18px; height: 18px; width: 18px">edit</mat-icon>
                    </button>
                    <button
                      type="button"
                      mat-icon-button
                      class="!text-red-400"
                      (click)="deleteAction.emit(a.id)"
                      matTooltip="Supprimer"
                    >
                      <mat-icon style="font-size: 18px; height: 18px; width: 18px">delete</mat-icon>
                    </button>
                  </div>
                </div>
              </div>
            }
          }
        </div>
      }
    </div>
  `,
})
export class ActionsTableComponent {
  @Input() filteredActions: RssiAction[] = [];
  @Input() totalActions = 0;
  @Input() statusFilter = 'all';
  @Input() priorityFilter = 'all';
  @Input() editingActionId: number | null = null;
  @Input() showAddForm = false;
  @Input() saving = false;
  @Input() exportingCsv = false;
  @Input() addForm!: FormGroup;
  @Input() editForm!: FormGroup;
  @Input() actionStatuses: LabelOption[] = [];
  @Input() actionPriorities: LabelOption[] = [];

  @Output() statusFilterChange = new EventEmitter<string>();
  @Output() priorityFilterChange = new EventEmitter<string>();
  @Output() exportCsv = new EventEmitter<void>();
  @Output() toggleAddForm = new EventEmitter<void>();
  @Output() addAction = new EventEmitter<void>();
  @Output() startEdit = new EventEmitter<RssiAction>();
  @Output() saveAction = new EventEmitter<number>();
  @Output() cancelEdit = new EventEmitter<void>();
  @Output() deleteAction = new EventEmitter<number>();

  readonly today = new Date().toISOString().slice(0, 10);

  submitAdd(): void {
    if (this.addForm.invalid) {
      this.addForm.markAllAsTouched();
      return;
    }
    this.addAction.emit();
  }

  submitEdit(id: number): void {
    if (this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    this.saveAction.emit(id);
  }

  formatDate(d: string | null): string {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  priorityClass(p: string): string {
    switch (p) {
      case 'critical':
        return 'text-red-400 bg-red-500/10 border-red-600/30';
      case 'high':
        return 'text-orange-400 bg-orange-500/10 border-orange-600/30';
      case 'medium':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-600/30';
      default:
        return 'text-gray-400 bg-gray-700/20 border-gray-600/30';
    }
  }

  actionStatusClass(s: string): string {
    switch (s) {
      case 'done':
        return 'text-green-400 bg-green-500/10 border-green-600/30';
      case 'in_progress':
        return 'text-blue-400 bg-blue-500/10 border-blue-600/30';
      case 'cancelled':
        return 'text-gray-500 bg-gray-700/20 border-gray-600/30';
      case 'postponed':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-600/30';
      default:
        return 'text-white bg-gray-700/30 border-gray-600/40';
    }
  }

  actionStatusLabel(s: string): string {
    const map: Record<string, string> = {
      open: 'Ouverte',
      in_progress: 'En cours',
      done: 'Terminée',
      cancelled: 'Annulée',
      postponed: 'Reportée',
    };
    return map[s] ?? s;
  }
}
