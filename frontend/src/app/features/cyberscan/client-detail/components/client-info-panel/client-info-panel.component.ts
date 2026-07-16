import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ReactiveFormsModule, FormGroup } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

interface FormulaOption {
  value: string;
  label: string;
}

@Component({
  standalone: true,
  selector: 'app-client-info-panel',
  imports: [ReactiveFormsModule, MatButtonModule, MatIconModule],
  template: `
    <form
      [formGroup]="form"
      (ngSubmit)="submitForm()"
      class="bg-gray-900 border border-gray-800 rounded-xl p-6"
    >
      <h2 class="text-sm font-semibold text-gray-300 mb-4">Informations client</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label class="block text-xs font-medium text-gray-400 mb-1.5"
            >Nom <span class="text-red-400">*</span></label
          >
          <input
            type="text"
            formControlName="name"
            placeholder="Acme Corp"
            class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-400 mb-1.5">Email</label>
          <input
            type="text"
            formControlName="email"
            placeholder="contact@client.com"
            class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
          />
        </div>
        <div class="md:col-span-2">
          <label class="block text-xs font-medium text-gray-400 mb-1.5">Description</label>
          <textarea
            formControlName="description"
            rows="2"
            placeholder="Notes…"
            class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all resize-y focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
          ></textarea>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-400 mb-1.5">Formule</label>
          <div class="relative">
            <select
              aria-label="Formule"
              formControlName="formula"
              class="w-full rounded-xl bg-gray-800/60 border border-gray-700 pl-3 pr-9 py-2.5 text-sm text-white outline-none appearance-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
            >
              <option value="">—</option>
              @for (f of formulas; track f.value) {
                <option [value]="f.value">{{ f.label }}</option>
              }
            </select>
            <mat-icon
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 !text-[1.15rem] !w-[1.15rem] !h-[1.15rem] pointer-events-none"
              >expand_more</mat-icon
            >
          </div>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-400 mb-1.5">Montant mensuel (€)</label>
          <input
            type="number"
            formControlName="monthly_amount"
            placeholder="0"
            class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-400 mb-1.5"
            >Renouvellement contrat</label
          >
          <input
            type="date"
            formControlName="contract_renewal_at"
            title="Date de renouvellement du contrat"
            class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white outline-none transition-all [color-scheme:dark] focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
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
              <option value="active">Actif</option>
              <option value="inactive">Inactif</option>
              <option value="churned">Churné</option>
            </select>
            <mat-icon
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 !text-[1.15rem] !w-[1.15rem] !h-[1.15rem] pointer-events-none"
              >expand_more</mat-icon
            >
          </div>
        </div>
      </div>

      <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
        Intégrations
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div>
          <label class="block text-xs font-medium text-gray-400 mb-1.5">Notion workspace URL</label>
          <input
            type="text"
            formControlName="notion_workspace_url"
            placeholder="https://notion.so/…"
            class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-400 mb-1.5">Pipedrive deal ID</label>
          <input
            type="text"
            formControlName="pipedrive_deal_id"
            placeholder="deal-123"
            class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-400 mb-1.5"
            >Pennylane customer ID</label
          >
          <input
            type="text"
            formControlName="pennylane_customer_id"
            placeholder="cust-456"
            class="w-full rounded-xl bg-gray-800/60 border border-gray-700 px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/70"
          />
        </div>
      </div>

      <div class="flex justify-end">
        <button
          mat-flat-button
          type="submit"
          [disabled]="saving"
          class="!rounded-xl !bg-cyan-600 hover:!bg-cyan-500 !text-sm"
        >
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

  submitForm(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.save.emit();
  }
}
