import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthStore } from '../auth.store';
import { OtpInputComponent } from '../../../shared/otp-input/otp-input.component';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, FormsModule, RouterLink,
    MatCardModule, MatFormFieldModule, MatInputModule,
    MatButtonModule, MatIconModule, MatProgressSpinnerModule, OtpInputComponent,
  ],
  providers: [AuthStore],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  readonly store = inject(AuthStore);

  get returnUrl(): string {
    return this.route.snapshot.queryParamMap.get('returnUrl') || '';
  }

  readonly loading$ = this.store.loading$;
  readonly error$ = this.store.error$;
  readonly requires2fa$ = this.store.requires2fa$;

  showPassword = false;
  totpCode = '';
  otpClear = 0;

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  submit() {
    if (this.form.valid) {
      this.store.login(this.form.getRawValue());
    }
  }

  submitTotp() {
    if (this.totpCode.length === 6) {
      this.store.loginWith2FA({ totpCode: this.totpCode });
    }
  }

  cancelTotp() {
    this.totpCode = '';
    this.otpClear++;
    this.store.cancelTwoFa();
  }
}
