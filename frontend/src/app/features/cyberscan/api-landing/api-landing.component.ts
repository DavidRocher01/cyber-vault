import { Component, inject, OnInit, signal } from '@angular/core';
import { NgClass } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { environment } from '../../../../environments/environment';

const API = environment.apiUrl;

const PLANS = [
  {
    name: 'Trial',
    price: 'Gratuit',
    quota: '50 scans',
    sites: '1 site',
    webhooks: '—',
    badge: null,
    highlight: false,
  },
  {
    name: 'Dev',
    price: '49 €/mois',
    quota: '500 scans',
    sites: '5 sites',
    webhooks: '1 webhook',
    badge: null,
    highlight: false,
  },
  {
    name: 'Pro',
    price: '199 €/mois',
    quota: '5 000 scans',
    sites: '50 sites',
    webhooks: '5 webhooks',
    badge: 'Populaire',
    highlight: true,
  },
  {
    name: 'Business',
    price: '499 €/mois',
    quota: '25 000 scans',
    sites: 'Illimité',
    webhooks: '20 webhooks',
    badge: null,
    highlight: false,
  },
];

const USE_CASES = [
  {
    icon: 'business',
    title: 'MSP & Infogérants',
    color: 'cyan',
    desc: "Automatisez l'audit mensuel de vos 40 clients PME. Un appel API le lundi matin, un rapport PDF par client à présenter en revue.",
    quote: '"40 clients, 0 audit manuel."',
    detail: '500–5 000 scans/mois · Plan Pro recommandé',
  },
  {
    icon: 'terminal',
    title: 'DevSecOps & CI/CD',
    color: 'purple',
    desc: 'Intégrez un check sécurité dans votre pipeline GitHub Actions. Si une faille critique apparaît, le déploiement échoue automatiquement.',
    quote: '"Security gate en 3 lignes de YAML."',
    detail: '100–500 scans/mois · Plan Dev recommandé (49 €/mois)',
  },
  {
    icon: 'api',
    title: 'Éditeurs SaaS',
    color: 'indigo',
    desc: "Affichez un score sécurité lors de l'onboarding de vos utilisateurs. Différenciez-vous sans développer le moteur.",
    quote: '"Score 0–100 pour chaque utilisateur."',
    detail: '5 000–25 000 scans/mois · Plan Business',
  },
];

const ROADMAP = [
  {
    sprint: 'S1',
    label: 'Auth clés API',
    desc: 'Génération, hachage bcrypt, révocation',
    done: false,
  },
  {
    sprint: 'S2',
    label: 'Comptage & quotas',
    desc: 'Redis usage counter, rate limiting',
    done: false,
  },
  {
    sprint: 'S3',
    label: 'Endpoints scans',
    desc: 'POST /v1/scans, GET /v1/scans/{id}',
    done: false,
  },
  {
    sprint: 'S4',
    label: 'Gestion des sites',
    desc: 'CRUD /v1/sites, vérification propriété',
    done: false,
  },
  { sprint: 'S5', label: 'Webhooks', desc: 'HMAC-SHA256, retry exponentiel', done: false },
  { sprint: 'S6', label: 'Facturation Stripe', desc: 'Plans API, overage metered', done: false },
  { sprint: 'S7', label: 'Dashboard API', desc: 'Section "API" dans le dashboard', done: false },
  {
    sprint: 'S8',
    label: 'Documentation',
    desc: 'docs.rochercybersecurite.com, quickstart',
    done: false,
  },
];

@Component({
  standalone: true,
  selector: 'app-api-landing',
  imports: [
    NgClass,
    ReactiveFormsModule,
    RouterLink,
    MatIconModule,
    MatProgressSpinnerModule,
    NavButtonsComponent,
  ],
  templateUrl: './api-landing.component.html',
})
export class ApiLandingComponent implements OnInit {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private titleService = inject(Title);
  private meta = inject(Meta);

  readonly plans = PLANS;
  readonly useCases = USE_CASES;
  readonly roadmap = ROADMAP;

  count = signal(0);
  loading = signal(false);
  success = signal(false);
  error = signal<string | null>(null);
  codeCopied = signal(false);

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    role: ['msp' as string, Validators.required],
    company: [''],
  });

  readonly curlExample = `curl -X POST https://api.rochercybersecurite.com/v1/scans \\
  -H "Authorization: Bearer csk_live_xxxx" \\
  -H "Content-Type: application/json" \\
  -d '{"url": "https://mon-client.fr"}'`;

  readonly responseExample = `{
  "scan_id": "scn_2a4f9c8d",
  "status": "pending",
  "verdict": null,
  "score": null,
  "estimated_completion_at": "2026-05-24T10:00:42Z"
}`;

  ngOnInit() {
    this.titleService.setTitle('API Rocher Cybersécurité — Automatisez vos audits de sécurité');
    this.meta.updateTag({
      name: 'description',
      content:
        "L'API Rocher Cybersécurité permet aux MSP, DevSecOps et éditeurs SaaS d'intégrer les scans de sécurité dans leurs outils. Rejoignez la liste d'attente.",
    });
    this.http.get<{ count: number }>(`${API}/api-waitlist/count`).subscribe({
      next: r => this.count.set(r.count),
      error: () => {},
    });
  }

  submit() {
    if (this.form.invalid || this.loading()) return;
    this.loading.set(true);
    this.error.set(null);
    this.http.post<{ count: number }>(`${API}/api-waitlist`, this.form.getRawValue()).subscribe({
      next: r => {
        this.count.set(r.count);
        this.success.set(true);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(
          err.status === 409
            ? 'Vous êtes déjà inscrit(e) sur la liste.'
            : 'Une erreur est survenue. Réessayez.'
        );
        this.loading.set(false);
      },
    });
  }

  copyCode() {
    navigator.clipboard.writeText(this.curlExample).then(() => {
      this.codeCopied.set(true);
      setTimeout(() => this.codeCopied.set(false), 2000);
    });
  }

  colorFor(color: string): string {
    const map: Record<string, string> = {
      cyan: 'text-cyan-400',
      purple: 'text-purple-400',
      indigo: 'text-indigo-400',
    };
    return map[color] ?? 'text-cyan-400';
  }

  borderFor(color: string): string {
    const map: Record<string, string> = {
      cyan: 'border-cyan-500/30',
      purple: 'border-purple-500/30',
      indigo: 'border-indigo-500/30',
    };
    return map[color] ?? 'border-cyan-500/30';
  }

  bgFor(color: string): string {
    const map: Record<string, string> = {
      cyan: 'bg-cyan-900/20',
      purple: 'bg-purple-900/20',
      indigo: 'bg-indigo-900/20',
    };
    return map[color] ?? 'bg-cyan-900/20';
  }
}
