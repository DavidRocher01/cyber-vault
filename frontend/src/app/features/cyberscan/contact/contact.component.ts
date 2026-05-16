import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

export const NEED_OPTIONS = [
  { value: 'audit-flash', label: 'Audit Flash — 245 € HT (site vitrine, blog)' },
  { value: 'audit-app', label: 'Audit App-Check — 725 € HT (SaaS, e-commerce)' },
  { value: 'pentest', label: 'Pentest léger — 1 900 € HT (données sensibles)' },
  { value: 'abonnement', label: 'Abonnement surveillance continue (~99–499 €/mois)' },
  { value: 'autre', label: 'Autre / Demande de devis' },
];

@Component({
  standalone: true,
  selector: 'app-contact',
  imports: [RouterLink, ReactiveFormsModule, MatIconModule, NavButtonsComponent],
  templateUrl: './contact.component.html',
})
export class ContactComponent implements OnInit {
  private titleService = inject(Title);
  private meta = inject(Meta);
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);

  readonly needOptions = NEED_OPTIONS;

  status: 'idle' | 'sending' | 'sent' | 'error' = 'idle';
  errorMessage = '';

  form: FormGroup = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    email: ['', [Validators.required, Validators.email]],
    phone: [''],
    need_type: ['', Validators.required],
    site_url: [''],
    message: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(2000)]],
    rgpd: [false, Validators.requiredTrue],
  });

  ngOnInit() {
    this.titleService.setTitle('Contact — Réserver un audit cybersécurité | CyberScan');
    this.meta.updateTag({
      name: 'description',
      content: 'Contactez David Rocher pour un audit cybersécurité PME. Réponse sous 4 h, devis sous 24 h.',
    });
  }

  get f() { return this.form.controls; }

  get messageLength(): number {
    return (this.f['message'].value as string)?.length ?? 0;
  }

  submit(): void {
    if (this.form.invalid || this.status === 'sending') return;
    this.status = 'sending';
    const { rgpd, ...payload } = this.form.value;
    this.http.post<{ message: string }>('/api/v1/contact', payload).subscribe({
      next: () => { this.status = 'sent'; },
      error: (err) => {
        this.status = 'error';
        this.errorMessage = err?.error?.detail ?? 'Une erreur est survenue. Réessayez ou écrivez directement à rocherdavid@ymail.com.';
      },
    });
  }
}
