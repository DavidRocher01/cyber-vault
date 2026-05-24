import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators, FormArray } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatStepperModule } from '@angular/material/stepper';
import { Title } from '@angular/platform-browser';

import { PcaService } from '../services/pca.service';
import { NavButtonsComponent } from '../../../shared/nav-buttons/nav-buttons.component';

@Component({
  standalone: true,
  selector: 'app-pca',
  imports: [
    CommonModule, ReactiveFormsModule,
    MatButtonModule, MatCardModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatProgressSpinnerModule,
    MatSnackBarModule, MatStepperModule, NavButtonsComponent,
  ],
  templateUrl: './pca.component.html',
  styleUrl: './pca.component.css',
})
export class PcaComponent {
  private pca = inject(PcaService);
  private fb = inject(FormBuilder);
  private snack = inject(MatSnackBar);
  private title = inject(Title);

  generating = signal(false);

  companyForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    sector: [''],
    contact: [''],
    email: [''],
    phone: [''],
  });

  systemsForm = this.fb.group({
    systems: this.fb.array([this._newSystem()]),
  });

  teamForm = this.fb.group({
    members: this.fb.array([this._newMember()]),
  });

  commForm = this.fb.nonNullable.group({
    communication_plan: [''],
  });

  constructor() {
    this.title.setTitle('PCA Light — CyberScan');
  }

  get systems(): FormArray { return this.systemsForm.get('systems') as FormArray; }
  get members(): FormArray { return this.teamForm.get('members') as FormArray; }

  private _newSystem() {
    return this.fb.nonNullable.group({
      name: ['', Validators.required],
      description: [''],
      rto_hours: [4, [Validators.required, Validators.min(1)]],
      rpo_hours: [1, [Validators.required, Validators.min(0)]],
      responsible: [''],
    });
  }

  private _newMember() {
    return this.fb.nonNullable.group({
      name: ['', Validators.required],
      role: [''],
      phone: [''],
      email: [''],
    });
  }

  addSystem() { this.systems.push(this._newSystem()); }
  removeSystem(i: number) { if (this.systems.length > 1) this.systems.removeAt(i); }
  addMember() { this.members.push(this._newMember()); }
  removeMember(i: number) { if (this.members.length > 1) this.members.removeAt(i); }

  generate() {
    if (this.companyForm.invalid) return;
    this.generating.set(true);

    const payload = {
      company: this.companyForm.getRawValue(),
      critical_systems: this.systems.controls
        .map(c => c.getRawValue())
        .filter((s: any) => s.name.trim()),
      response_team: this.members.controls
        .map(c => c.getRawValue())
        .filter((m: any) => m.name.trim()),
      communication_plan: this.commForm.getRawValue().communication_plan,
    };

    this.pca.generate(payload).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pca_${payload.company.name.replace(/\s+/g, '_').toLowerCase()}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        this.generating.set(false);
        this.snack.open('PCA téléchargé', 'OK', { duration: 3000 });
      },
      error: () => {
        this.generating.set(false);
        this.snack.open('Erreur lors de la génération', 'Fermer', { duration: 4000 });
      },
    });
  }
}
