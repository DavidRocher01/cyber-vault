import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ReactiveFormsModule, FormGroup } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RssiAction } from '../../../services/rssi.service';

interface LabelOption {
  value: string;
  label: string;
}

@Component({
  standalone: true,
  selector: 'app-actions-table',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  template: `
    <div>
      <div class="flex flex-wrap items-center gap-3 mb-4">
        <h2 class="text-sm font-semibold text-gray-300 mr-auto">Plan d'actions</h2>
        <!-- Filtres -->
        <mat-form-field appearance="outline" class="!w-36 !text-sm">
          <mat-label>Statut</mat-label>
          <mat-select [value]="statusFilter" (valueChange)="statusFilterChange.emit($event)">
            <mat-option value="all">Tous</mat-option>
            @for (s of actionStatuses; track s.value) {
              <mat-option [value]="s.value">{{ s.label }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline" class="!w-36 !text-sm">
          <mat-label>Priorité</mat-label>
          <mat-select [value]="priorityFilter" (valueChange)="priorityFilterChange.emit($event)">
            <mat-option value="all">Toutes</mat-option>
            @for (p of actionPriorities; track p.value) {
              <mat-option [value]="p.value">{{ p.label }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
        <button
          type="button"
          mat-stroked-button
          (click)="exportCsv.emit()"
          [disabled]="exportingCsv"
          matTooltip="Exporter en CSV (compatible Excel)"
        >
          @if (exportingCsv) {
            <mat-icon class="animate-spin">sync</mat-icon>
          } @else {
            <mat-icon>download</mat-icon>
          }
          CSV
        </button>
        <button type="button" mat-flat-button color="primary" (click)="toggleAddForm.emit()">
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
          <mat-form-field appearance="outline" class="w-full md:col-span-2">
            <mat-label>Titre *</mat-label>
            <input matInput formControlName="title" placeholder="Mettre en place MFA…" />
            <mat-error>Ce champ est requis.</mat-error>
          </mat-form-field>
          <mat-form-field appearance="outline" class="w-full">
            <mat-label>Priorité</mat-label>
            <mat-select formControlName="priority">
              @for (p of actionPriorities; track p.value) {
                <mat-option [value]="p.value">{{ p.label }}</mat-option>
              }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline" class="w-full md:col-span-3">
            <mat-label>Description</mat-label>
            <textarea
              matInput
              formControlName="description"
              rows="2"
              placeholder="Détails…"
            ></textarea>
          </mat-form-field>
          <mat-form-field appearance="outline" class="w-full">
            <mat-label>Catégorie</mat-label>
            <mat-select formControlName="category">
              <mat-option value="">—</mat-option>
              <mat-option value="governance">Gouvernance</mat-option>
              <mat-option value="technical">Technique</mat-option>
              <mat-option value="training">Formation</mat-option>
              <mat-option value="compliance">Conformité</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline" class="w-full">
            <mat-label>Responsable</mat-label>
            <input matInput formControlName="assigned_to" placeholder="ciso@client.com" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="w-full">
            <mat-label>Échéance</mat-label>
            <input
              matInput
              type="date"
              formControlName="due_date"
              title="Date d'échéance de l'action"
            />
          </mat-form-field>
          <div class="md:col-span-3 flex justify-end gap-2">
            <button type="button" mat-stroked-button (click)="toggleAddForm.emit()">Annuler</button>
            <button mat-flat-button color="primary" type="submit" [disabled]="saving">Créer</button>
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
                <mat-form-field appearance="outline" class="w-full md:col-span-2">
                  <mat-label>Titre *</mat-label>
                  <input matInput formControlName="title" placeholder="Titre de l'action" />
                  <mat-error>Ce champ est requis.</mat-error>
                </mat-form-field>
                <mat-form-field appearance="outline" class="w-full">
                  <mat-label>Statut</mat-label>
                  <mat-select formControlName="status">
                    @for (s of actionStatuses; track s.value) {
                      <mat-option [value]="s.value">{{ s.label }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                <mat-form-field appearance="outline" class="w-full md:col-span-3">
                  <mat-label>Description</mat-label>
                  <textarea
                    matInput
                    formControlName="description"
                    rows="2"
                    placeholder="Détails de l'action…"
                  ></textarea>
                </mat-form-field>
                <mat-form-field appearance="outline" class="w-full">
                  <mat-label>Catégorie</mat-label>
                  <mat-select formControlName="category">
                    <mat-option value="">—</mat-option>
                    <mat-option value="governance">Gouvernance</mat-option>
                    <mat-option value="technical">Technique</mat-option>
                    <mat-option value="training">Formation</mat-option>
                    <mat-option value="compliance">Conformité</mat-option>
                  </mat-select>
                </mat-form-field>
                <mat-form-field appearance="outline" class="w-full">
                  <mat-label>Priorité</mat-label>
                  <mat-select formControlName="priority">
                    @for (p of actionPriorities; track p.value) {
                      <mat-option [value]="p.value">{{ p.label }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                <mat-form-field appearance="outline" class="w-full">
                  <mat-label>Responsable</mat-label>
                  <input matInput formControlName="assigned_to" placeholder="ciso@client.com" />
                </mat-form-field>
                <mat-form-field appearance="outline" class="w-full">
                  <mat-label>Échéance</mat-label>
                  <input
                    matInput
                    type="date"
                    formControlName="due_date"
                    title="Date d'échéance de l'action"
                  />
                </mat-form-field>
                <div class="md:col-span-3 flex justify-end gap-2">
                  <button type="button" mat-stroked-button (click)="cancelEdit.emit()">
                    Annuler
                  </button>
                  <button mat-flat-button color="primary" type="submit">Enregistrer</button>
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
