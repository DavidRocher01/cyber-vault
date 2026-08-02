import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { extractApiError } from '../../../core/http-error';
import { PLAN_ENTREE, REMISE_PARTENAIRE } from '../../../shared/awareness-plans';

export const NEED_OPTIONS = [
  { value: 'rssi-externalise', label: 'RSSI externalisé — votre RSSI à temps partagé (sur devis)' },
  { value: 'audit-flash', label: 'Audit Flash — 390 € HT (site vitrine, blog)' },
  { value: 'audit-app', label: 'Audit App-Check — 990 € HT (SaaS, e-commerce)' },
  { value: 'pentest', label: 'Pentest léger — 2 490 € HT (données sensibles)' },
  { value: 'audit-nis2', label: 'Audit NIS2 / RGPD — 1 290 € HT (entités NIS2)' },
  { value: 'simulation-phishing', label: 'Simulation de phishing — à partir de 990 € HT' },
  {
    value: 'sensibilisation-nis2',
    label: `Formation NIS2 — Sensibilisation équipes (dès ${PLAN_ENTREE.price} €/mois)`,
  },
  {
    value: 'partenaire-sensibilisation',
    label: `Partenaire consultant RSSI — formation de vos clients (-${Math.round(REMISE_PARTENAIRE * 100)} %)`,
  },
  { value: 'abonnement', label: 'Abonnement surveillance continue (49–390 €/mois)' },
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
  private route = inject(ActivatedRoute);
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
    // Le parametre ?subject= etait passe par les liens des pages tarifs mais
    // n'etait lu NULLE PART : une demande partenaire arrivait indistinguable
    // d'un contact ordinaire. On pre-selectionne le type de besoin quand la
    // valeur correspond a une option connue.
    const sujet = this.route.snapshot.queryParamMap.get('subject');
    if (sujet && NEED_OPTIONS.some(o => o.value === sujet)) {
      this.form.patchValue({ need_type: sujet });
    }

    this.titleService.setTitle('Contact — Réserver un audit cybersécurité | Rocher Cybersécurité');
    this.meta.updateTag({
      name: 'description',
      content:
        'Contactez David Rocher pour un audit cybersécurité PME. Réponse sous 4 h, devis sous 24 h.',
    });
  }

  get f() {
    return this.form.controls;
  }

  get messageLength(): number {
    return (this.f['message'].value as string)?.length ?? 0;
  }

  submit(): void {
    if (this.form.invalid || this.status === 'sending') return;
    this.status = 'sending';
    const { rgpd, ...payload } = this.form.value;
    this.http.post<{ message: string }>('/api/v1/contact', payload).subscribe({
      next: () => {
        this.status = 'sent';
      },
      error: err => {
        this.status = 'error';
        this.errorMessage = extractApiError(
          err,
          'Une erreur est survenue. Réessayez ou écrivez directement à rocherdavid@ymail.com.'
        );
      },
    });
  }
}
