import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router } from '@angular/router';
import { NgxSkeletonLoaderModule } from 'ngx-skeleton-loader';
import { combineLatest, map, take } from 'rxjs';

import { HotToastService } from '@ngneat/hot-toast';

import { AuthService } from '../../../core/services/auth.service';
import { CryptoService } from '../../../core/services/crypto.service';
import { ClipboardService } from '../../../core/services/clipboard.service';
import { PasswordGeneratorService } from '../../../core/services/password-generator.service';
import { VaultStore } from '../vault.store';
import { VaultItem } from '../../../core/services/vault.service';

@Component({
  selector: 'app-vault-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatToolbarModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatTooltipModule,
    NgxSkeletonLoaderModule,
  ],
  providers: [VaultStore],
  templateUrl: './vault-dashboard.component.html',
})
export class VaultDashboardComponent implements OnInit {
  private store = inject(VaultStore);
  private authService = inject(AuthService);
  private cryptoService = inject(CryptoService);
  private clipboardService = inject(ClipboardService);
  private passwordGenerator = inject(PasswordGeneratorService);
  private toast = inject(HotToastService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  readonly loading$ = this.store.loading$;
  readonly error$ = this.store.error$;

  searchQuery = '';
  readonly filteredItems$ = combineLatest([this.store.items$]).pipe(
    map(([items]) =>
      items.filter(item =>
        !this.searchQuery ||
        item.title.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        (item.username ?? '').toLowerCase().includes(this.searchQuery.toLowerCase())
      )
    )
  );

  showForm = false;
  form = this.fb.nonNullable.group({
    title: ['', Validators.required],
    username: [''],
    password_encrypted: ['', Validators.required],
    url: [''],
    notes: [''],
  });

  revealedPasswords: Record<number, string | null> = {};
  copiedId: number | null = null;

  ngOnInit() {
    this.store.loadItems();
  }

  onSearch(value: string) {
    this.searchQuery = value;
  }

  generatePassword() {
    const pwd = this.passwordGenerator.generate(20);
    this.form.patchValue({ password_encrypted: pwd });
  }

  submit() {
    if (this.form.invalid) return;
    this.store.createItem(this.form.getRawValue());
    this.form.reset();
    this.showForm = false;
    this.toast.success('Entrée ajoutée');
  }

  delete(id: number) {
    this.store.deleteItem(id);
    delete this.revealedPasswords[id];
    this.toast.success('Entrée supprimée');
  }

  async toggleReveal(item: VaultItem) {
    if (this.revealedPasswords[item.id] !== undefined) {
      delete this.revealedPasswords[item.id];
      return;
    }
    try {
      const plain = await this.cryptoService.decrypt(item.password_encrypted);
      this.revealedPasswords[item.id] = plain;
    } catch {
      this.revealedPasswords[item.id] = null;
      this.toast.error('Erreur de déchiffrement');
    }
  }

  async copyPassword(item: VaultItem) {
    try {
      const plain = await this.cryptoService.decrypt(item.password_encrypted);
      this.clipboardService.copy(plain);
      this.copiedId = item.id;
      this.toast.success('Mot de passe copié — presse-papiers effacé dans 30s');
      setTimeout(() => { if (this.copiedId === item.id) this.copiedId = null; }, 2000);
    } catch {
      this.toast.error('Erreur de déchiffrement');
    }
  }

  exportVault() {
    this.store.items$.pipe(take(1)).subscribe(items => {
      const data = items.map(item => ({
        title: item.title,
        username: item.username,
        password_encrypted: item.password_encrypted,
        url: item.url,
        notes: item.notes,
        exported_at: new Date().toISOString(),
      }));
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cyber-vault-export-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      this.toast.success('Export téléchargé (données chiffrées)');
    });
  }

  logout() {
    this.authService.logout();
    this.cryptoService.clearKey();
    this.router.navigate(['/auth/login']);
  }
}
