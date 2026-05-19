import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormArray, Validators, AbstractControl } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AdminAuthService } from '../admin-auth.service';

interface QuoteItem {
  description: string;
  quantity: number;
  unit_price_cents: number;
}

interface AdminQuote {
  id: number;
  quote_number: string;
  client_name: string;
  client_email: string;
  client_address: string | null;
  subject: string;
  items: QuoteItem[];
  total_cents: number;
  total_eur: number;
  validity_days: number;
  status: string;
  issue_date: string;
  created_at: string;
}

const API = '/api/v1';

@Component({
  standalone: true,
  selector: 'app-admin-quotes',
  imports: [
    CommonModule, ReactiveFormsModule,
    MatIconModule, MatSnackBarModule, MatProgressSpinnerModule,
  ],
  templateUrl: './admin-quotes.component.html',
})
export class AdminQuotesComponent implements OnInit {
  private http  = inject(HttpClient);
  private auth  = inject(AdminAuthService);
  private fb    = inject(FormBuilder);
  private snack = inject(MatSnackBar);

  quotes          = signal<AdminQuote[]>([]);
  loading         = signal(true);
  creating        = signal(false);
  showForm        = signal(false);
  downloading     = signal<number | null>(null);
  submitAttempted = signal(false);

  form = this.fb.group({
    client_name:    ['', Validators.required],
    client_email:   ['', [Validators.required, Validators.email]],
    client_address: [''],
    subject:        ['', Validators.required],
    validity_days:  [30, [Validators.required, Validators.min(1)]],
    user_email:     [''],
    issue_date:     [''],
    items: this.fb.array([this.newItemGroup()]),
  });

  private get headers(): HttpHeaders { return this.auth.headers(); }

  get itemsArray(): FormArray { return this.form.get('items') as FormArray; }

  newItemGroup() {
    return this.fb.group({
      description:      ['', Validators.required],
      quantity:         [1,  [Validators.required, Validators.min(1)]],
      unit_price_eur:   [null as number | null, [Validators.required, Validators.min(0)]],
    });
  }

  addItem() { this.itemsArray.push(this.newItemGroup()); }

  removeItem(i: number) {
    if (this.itemsArray.length > 1) this.itemsArray.removeAt(i);
  }

  lineTotal(i: number): number {
    const g = this.itemsArray.at(i);
    return (g.value.quantity ?? 0) * (g.value.unit_price_eur ?? 0);
  }

  get grandTotal(): number {
    return this.itemsArray.controls.reduce((sum, _, i) => sum + this.lineTotal(i), 0);
  }

  ctrl(name: string): AbstractControl { return this.form.get(name)!; }
  itemCtrl(i: number, name: string): AbstractControl { return this.itemsArray.at(i).get(name)!; }

  ngOnInit() { this.load(); }

  load() {
    this.loading.set(true);
    this.http.get<AdminQuote[]>(`${API}/admin/quotes`, { headers: this.headers }).subscribe({
      next: data => { this.quotes.set(data); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  submit() {
    this.submitAttempted.set(true);
    if (this.form.invalid) return;
    const v = this.form.getRawValue();
    const body = {
      client_name:    v.client_name,
      client_email:   v.client_email,
      client_address: v.client_address || null,
      subject:        v.subject,
      validity_days:  v.validity_days ?? 30,
      user_email:     v.user_email || null,
      issue_date:     v.issue_date || null,
      items: (v.items ?? []).map((item: any) => ({
        description:      item.description,
        quantity:         item.quantity,
        unit_price_cents: Math.round((item.unit_price_eur ?? 0) * 100),
      })),
    };
    this.creating.set(true);
    this.http.post<AdminQuote>(`${API}/admin/quotes`, body, { headers: this.headers }).subscribe({
      next: q => {
        this.quotes.update(list => [q, ...list]);
        this.form.reset();
        this.itemsArray.clear();
        this.itemsArray.push(this.newItemGroup());
        this.showForm.set(false);
        this.creating.set(false);
        this.submitAttempted.set(false);
        this.snack.open(`Devis ${q.quote_number} créé et envoyé par email`, 'OK', { duration: 5000 });
      },
      error: err => {
        this.creating.set(false);
        this.snack.open(err.error?.detail || 'Erreur lors de la création', 'Fermer', { duration: 5000 });
      },
    });
  }

  download(q: AdminQuote) {
    this.downloading.set(q.id);
    this.http.get(`${API}/admin/quotes/${q.id}/pdf`, {
      headers: this.headers, responseType: 'blob',
    }).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `${q.quote_number}.pdf`; a.click();
        URL.revokeObjectURL(url);
        this.downloading.set(null);
      },
      error: () => {
        this.snack.open('Erreur téléchargement PDF', 'Fermer', { duration: 4000 });
        this.downloading.set(null);
      },
    });
  }

  formatAmount(cents: number): string {
    return (cents / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('fr-FR');
  }

  statusLabel(s: string): string {
    return { sent: 'Envoyé', accepted: 'Accepté', rejected: 'Refusé', expired: 'Expiré' }[s] ?? s;
  }

  statusClasses(s: string): string {
    return {
      sent:     'bg-blue-900 text-blue-300 border-blue-700',
      accepted: 'bg-green-900 text-green-300 border-green-700',
      rejected: 'bg-red-900 text-red-300 border-red-700',
      expired:  'bg-gray-800 text-gray-400 border-gray-600',
    }[s] ?? 'bg-gray-800 text-gray-400 border-gray-600';
  }
}
