import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Title } from '@angular/platform-browser';

import { DarkwebDossierService } from '../services/darkweb-dossier.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-darkweb-dossier-new',
  imports: [
    RouterLink, ReactiveFormsModule,
    MatButtonModule, MatFormFieldModule, MatIconModule,
    MatInputModule, MatProgressSpinnerModule, MatSnackBarModule,
    NavButtonsComponent,
  ],
  templateUrl: './darkweb-dossier-new.component.html',
})
export class DarkwebDossierNewComponent {
  private service = inject(DarkwebDossierService);
  private router = inject(Router);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  form = new FormGroup({
    company_name: new FormControl('', [Validators.required, Validators.minLength(2), Validators.maxLength(200)]),
    domain: new FormControl('', [
      Validators.required,
      Validators.pattern(/^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/),
    ]),
  });

  csvFile = signal<File | null>(null);
  csvError = signal<string | null>(null);
  emailPreview = signal<string[]>([]);
  submitting = signal(false);

  constructor() {
    this.title.setTitle('Nouveau dossier — Dark Web | CyberScan');
  }

  onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.csvFile.set(file);
    this.csvError.set(null);
    this.emailPreview.set([]);

    if (!file) return;
    if (!file.name.endsWith('.csv') && file.type !== 'text/csv') {
      this.csvError.set('Format invalide — seuls les fichiers .csv sont acceptés');
      this.csvFile.set(null);
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      this.csvError.set('Fichier trop lourd — maximum 2 Mo');
      this.csvFile.set(null);
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = (e.target?.result as string) || '';
      const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
      const emails = lines
        .flatMap(l => l.split(','))
        .map(v => v.trim().toLowerCase().replace(/^"|"$/g, ''))
        .filter(v => v.includes('@') && v.includes('.'));
      this.emailPreview.set(emails.slice(0, 5));
      if (emails.length === 0) {
        this.csvError.set('Aucun email valide trouvé dans ce fichier');
        this.csvFile.set(null);
      }
    };
    reader.readAsText(file);
  }

  get canSubmit(): boolean {
    return this.form.valid && !!this.csvFile() && !this.submitting();
  }

  submit() {
    if (!this.canSubmit) return;
    const { company_name, domain } = this.form.value;
    this.submitting.set(true);
    this.service.create(company_name!, domain!, this.csvFile()!).subscribe({
      next: (d) => {
        this.submitting.set(false);
        this.snack.open('Dossier créé — analyse en cours', 'OK', { duration: 4000 });
        this.router.navigate(['/cyberscan/darkweb-dossier', d.id]);
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err?.error?.detail || 'Erreur lors de la création du dossier';
        this.snack.open(msg, 'Fermer', { duration: 5000 });
      },
    });
  }
}
