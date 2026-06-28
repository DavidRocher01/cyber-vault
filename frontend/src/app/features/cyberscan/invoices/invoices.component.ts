import { Component, inject, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { Title } from '@angular/platform-browser';

import { CyberscanService, Invoice, PaginatedInvoices } from '../services/cyberscan.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-invoices',
  imports: [
    MatButtonModule,
    MatIconModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    NavButtonsComponent,
  ],
  templateUrl: './invoices.component.html',
  styleUrl: './invoices.component.css',
})
export class InvoicesComponent implements OnInit {
  private service = inject(CyberscanService);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  data = signal<PaginatedInvoices | null>(null);
  loading = signal(true);
  selected = signal<Invoice | null>(null);
  downloading = signal<number | null>(null);

  ngOnInit() {
    this.title.setTitle('Mes factures — CyberScan');
    this.load(1);
  }

  load(page: number) {
    this.loading.set(true);
    this.service.getMyInvoices(page).subscribe({
      next: d => {
        this.data.set(d);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  onPage(event: PageEvent) {
    this.load(event.pageIndex + 1);
  }

  selectInvoice(inv: Invoice) {
    this.selected.set(this.selected()?.id === inv.id ? null : inv);
  }

  download(inv: Invoice, event: MouseEvent) {
    event.stopPropagation();
    this.downloading.set(inv.id);
    this.service.downloadInvoicePdfBlob(inv.id).subscribe({
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
        this.snack.open('Erreur lors du téléchargement', 'Fermer', { duration: 4000 });
        this.downloading.set(null);
      },
    });
  }

  formatAmount(cents: number): string {
    return (cents / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  typeLabel(type: string): string {
    return type === 'subscription' ? 'Abonnement' : 'Audit';
  }

  typeClass(type: string): string {
    return type === 'subscription'
      ? 'bg-blue-500/20 text-blue-300 border-blue-700'
      : 'bg-purple-500/20 text-purple-300 border-purple-700';
  }
}
