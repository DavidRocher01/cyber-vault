import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Title } from '@angular/platform-browser';

import { UserService, UserProfile } from '../services/user.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, RouterLink,
    MatButtonModule, MatCardModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatSnackBarModule, MatDividerModule, MatProgressSpinnerModule,
  ],
  templateUrl: './profile.component.html',
})
export class ProfileComponent implements OnInit {
  private userService = inject(UserService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  profile = signal<UserProfile | null>(null);
  loading = signal(true);
  savingEmail = signal(false);
  savingPassword = signal(false);

  emailForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    current_password: ['', Validators.required],
  });

  passwordForm = this.fb.nonNullable.group({
    current_password: ['', Validators.required],
    new_password: ['', [Validators.required, Validators.minLength(8)]],
    confirm_password: ['', Validators.required],
  });

  ngOnInit() {
    this.title.setTitle('Mon profil — CyberScan');
    this.userService.getProfile().subscribe({
      next: p => {
        this.profile.set(p);
        this.emailForm.patchValue({ email: p.email });
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  updateEmail() {
    if (this.emailForm.invalid) return;
    this.savingEmail.set(true);
    const { email, current_password } = this.emailForm.getRawValue();
    this.userService.updateEmail(email, current_password).subscribe({
      next: p => {
        this.profile.set(p);
        this.emailForm.patchValue({ current_password: '' });
        this.savingEmail.set(false);
        this.snack.open('Email mis à jour', 'OK', { duration: 3000 });
      },
      error: err => {
        this.savingEmail.set(false);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }

  updatePassword() {
    const { new_password, confirm_password, current_password } = this.passwordForm.getRawValue();
    if (this.passwordForm.invalid) return;
    if (new_password !== confirm_password) {
      this.snack.open('Les mots de passe ne correspondent pas', 'Fermer', { duration: 4000 });
      return;
    }
    this.savingPassword.set(true);
    this.userService.updatePassword(current_password, new_password).subscribe({
      next: () => {
        this.passwordForm.reset();
        this.savingPassword.set(false);
        this.snack.open('Mot de passe mis à jour', 'OK', { duration: 3000 });
      },
      error: err => {
        this.savingPassword.set(false);
        this.snack.open(err.error?.detail || 'Erreur', 'Fermer', { duration: 4000 });
      },
    });
  }
}
