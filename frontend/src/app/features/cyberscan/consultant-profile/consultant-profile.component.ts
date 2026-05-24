import { Component, inject, signal, OnInit } from '@angular/core';
import { ReactiveFormsModule, FormBuilder } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';
import { RssiService } from '../services/rssi.service';

@Component({
  standalone: true,
  selector: 'app-consultant-profile',
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    NavButtonsComponent,
  ],
  templateUrl: './consultant-profile.component.html',
})
export class ConsultantProfileComponent implements OnInit {
  private rssi = inject(RssiService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  loading = signal(true);
  saving = signal(false);
  saved = signal(false);

  form = this.fb.nonNullable.group({
    display_name: [''],
    company_name: [''],
    phone: [''],
  });

  ngOnInit() {
    this.rssi.getProfile().subscribe({
      next: p => {
        this.form.patchValue({
          display_name: p.display_name ?? '',
          company_name: p.company_name ?? '',
          phone: p.phone ?? '',
        });
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  save() {
    this.saving.set(true);
    this.rssi.updateProfile(this.form.getRawValue()).subscribe({
      next: () => {
        this.saving.set(false);
        this.saved.set(true);
        setTimeout(() => this.saved.set(false), 2500);
      },
      error: () => this.saving.set(false),
    });
  }

  back() {
    this.router.navigate(['/cyberscan/consultant']);
  }
}
