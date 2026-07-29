import { Component, inject, signal, OnInit } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { snackApiError } from '../../../core/snack-error';
import { RssiService } from '../services/rssi.service';

/** Permissif volontairement : chiffres, espaces, points, tirets, parentheses et
 *  indicatif international. Un format strict rejetterait des numeros etrangers
 *  valides pour un champ purement informatif imprime sur le rapport. */
const PHONE_PATTERN = /^[+0-9][0-9 .\-()]{5,}$/;

@Component({
  standalone: true,
  selector: 'app-consultant-profile',
  imports: [ReactiveFormsModule, MatButtonModule, MatIconModule, NavButtonsComponent],
  templateUrl: './consultant-profile.component.html',
})
export class ConsultantProfileComponent implements OnInit {
  private rssi = inject(RssiService);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);

  loading = signal(true);
  saving = signal(false);
  saved = signal(false);

  form = this.fb.nonNullable.group({
    // Obligatoire : c'est le nom imprime en en-tete de chaque rapport client.
    display_name: ['', [Validators.required, Validators.maxLength(120)]],
    company_name: ['', [Validators.maxLength(120)]],
    phone: ['', [Validators.pattern(PHONE_PATTERN), Validators.maxLength(30)]],
  });

  ngOnInit() {
    this.rssi.getProfile().subscribe({
      next: p => {
        this.form.patchValue({
          display_name: p.display_name ?? '',
          company_name: p.company_name ?? '',
          phone: p.phone ?? '',
        });
        this.form.markAsPristine();
        this.loading.set(false);
      },
      error: err => {
        this.loading.set(false);
        // L'echec de chargement etait totalement silencieux : l'utilisateur
        // voyait un formulaire vide et pouvait ecraser son profil existant.
        snackApiError(this.snack, err, 'Impossible de charger votre profil');
      },
    });
  }

  /** Champ en erreur ET deja touche — evite de colorer en rouge un formulaire
   *  vierge que l'utilisateur n'a pas encore rempli. */
  isInvalid(field: string): boolean {
    const c = this.form.get(field);
    return !!c && c.invalid && (c.touched || c.dirty);
  }

  save() {
    if (this.form.invalid) {
      // Sans cela, un submit clavier sur formulaire invalide ne montrait rien.
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.rssi.updateProfile(this.form.getRawValue()).subscribe({
      next: () => {
        this.saving.set(false);
        this.saved.set(true);
        this.form.markAsPristine();
        setTimeout(() => this.saved.set(false), 2500);
      },
      error: err => {
        this.saving.set(false);
        // L'echec de sauvegarde etait silencieux : le bouton redevenait normal
        // et l'utilisateur croyait son profil enregistre.
        snackApiError(this.snack, err, 'Enregistrement impossible');
      },
    });
  }

  get displayInitials(): string {
    const name = this.form.value.display_name ?? '';
    return name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((w: string) => w[0] ?? '')
      .join('')
      .toUpperCase();
  }

  back() {
    if (this.form.dirty && !confirm('Modifications non enregistrées. Quitter quand même ?')) {
      return;
    }
    this.router.navigate(['/consultant']);
  }
}
