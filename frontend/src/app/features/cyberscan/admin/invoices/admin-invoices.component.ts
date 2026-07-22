import { Component, inject, OnInit, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators, AbstractControl } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { AdminAuthService } from '../admin-auth.service';
import { extractApiError } from '../../../../core/http-error';

interface AdminInvoice {
  id: number;
  invoice_number: string;
  type: string;
  user_id: number | null;
  client_name: string;
  client_email: string;
  client_address: string | null;
  description: string;
  amount_cents: number;
  amount_eur: number;
  status: string;
  issue_date: string;
  created_at: string;
}

const API = '/api/v1';

@Component({
  standalone: true,
  selector: 'app-admin-invoices',
  imports: [ReactiveFormsModule, MatIconModule, MatSnackBarModule, MatProgressSpinnerModule],
  templateUrl: './admin-invoices.component.html',
})
export class AdminInvoicesComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AdminAuthService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);

  invoices = signal<AdminInvoice[]>([]);
  loading = signal(true);
  creating = signal(false);
  showForm = signal(false);
  downloading = signal<number | null>(null);
  submitAttempted = signal(false);

  form = this.fb.group({
    client_name: ['', Validators.required],
    client_email: ['', [Validators.required, Validators.email]],
    client_address: [''],
    description: ['', Validators.required],
    amount_eur: [null as number | null, [Validators.required, Validators.min(0.01)]],
    user_email: [''],
    issue_date: [''],
  });

  private get headers(): HttpHeaders {
    return this.auth.headers();
  }

  ngOnInit() {
    this.load();
  }

  load() {
    this.loading.set(true);
    this.http.get<AdminInvoice[]>(`${API}/admin/invoices`, { headers: this.headers }).subscribe({
      next: data => {
        this.invoices.set(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  submit() {
    this.submitAttempted.set(true);
    if (this.form.invalid) return;
    const v = this.form.getRawValue();
    const body = {
      client_name: v.client_name,
      client_email: v.client_email,
      client_address: v.client_address || null,
      description: v.description,
      amount_cents: Math.round((v.amount_eur ?? 0) * 100),
      user_email: v.user_email || null,
      issue_date: v.issue_date || null,
    };
    this.creating.set(true);
    this.http
      .post<AdminInvoice>(`${API}/admin/invoices`, body, { headers: this.headers })
      .subscribe({
        next: inv => {
          this.invoices.update(list => [inv, ...list]);
          this.form.reset();
          this.showForm.set(false);
          this.creating.set(false);
          this.snack.open(`Facture ${inv.invoice_number} créée`, 'OK', { duration: 4000 });
        },
        error: err => {
          this.creating.set(false);
          this.snack.open(extractApiError(err, 'Erreur lors de la création'), 'Fermer', {
            duration: 5000,
          });
        },
      });
  }

  download(inv: AdminInvoice) {
    this.downloading.set(inv.id);
    this.http
      .get(`${API}/admin/invoices/${inv.id}/pdf`, {
        headers: this.headers,
        responseType: 'blob',
      })
      .subscribe({
        next: blob => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${inv.invoice_number}.pdf`;
          a.click();
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

  ctrl(name: string): AbstractControl {
    return this.form.get(name)!;
  }
}
