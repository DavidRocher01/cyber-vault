import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ReactiveFormsModule, FormGroup } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';

interface FormulaOption {
  value: string;
  label: string;
}

@Component({
  standalone: true,
  selector: 'app-client-info-panel',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
  ],
  template: `
    <form
      [formGroup]="form"
      (ngSubmit)="save.emit()"
      class="bg-gray-900 border border-gray-800 rounded-xl p-6"
    >
      <h2 class="text-sm font-semibold text-gray-300 mb-4">Informations client</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Nom *</mat-label>
          <input matInput formControlName="name" placeholder="Acme Corp" />
        </mat-form-field>
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Email</mat-label>
          <input matInput formControlName="email" placeholder="contact@client.com" />
        </mat-form-field>
        <mat-form-field appearance="outline" class="w-full md:col-span-2">
          <mat-label>Description</mat-label>
          <textarea matInput formControlName="description" rows="2" placeholder="Notes…"></textarea>
        </mat-form-field>
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Formule</mat-label>
          <mat-select formControlName="formula">
            <mat-option value="">—</mat-option>
            @for (f of formulas; track f.value) {
              <mat-option [value]="f.value">{{ f.label }}</mat-option>
            }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Montant mensuel (€)</mat-label>
          <input matInput type="number" formControlName="monthly_amount" placeholder="0" />
        </mat-form-field>
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Renouvellement contrat</mat-label>
          <input
            matInput
            type="date"
            formControlName="contract_renewal_at"
            title="Date de renouvellement du contrat"
          />
        </mat-form-field>
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Statut</mat-label>
          <mat-select formControlName="status">
            <mat-option value="active">Actif</mat-option>
            <mat-option value="inactive">Inactif</mat-option>
            <mat-option value="churned">Churné</mat-option>
          </mat-select>
        </mat-form-field>
      </div>

      <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
        Intégrations
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Notion workspace URL</mat-label>
          <input
            matInput
            formControlName="notion_workspace_url"
            placeholder="https://notion.so/…"
          />
        </mat-form-field>
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Pipedrive deal ID</mat-label>
          <input matInput formControlName="pipedrive_deal_id" placeholder="deal-123" />
        </mat-form-field>
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Pennylane customer ID</mat-label>
          <input matInput formControlName="pennylane_customer_id" placeholder="cust-456" />
        </mat-form-field>
      </div>

      <div class="flex justify-end">
        <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid || saving">
          <mat-icon>save</mat-icon>
          {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
      </div>
    </form>
  `,
})
export class ClientInfoPanelComponent {
  @Input() form!: FormGroup;
  @Input() saving = false;
  @Input() formulas: FormulaOption[] = [];

  @Output() save = new EventEmitter<void>();
}
