import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ReactiveFormsModule, FormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';
import { combineLatest, filter, map, take } from 'rxjs';

import { HotToastService } from '@ngneat/hot-toast';

import { AuthService } from '../../../core/services/auth.service';
import { CryptoService } from '../../../core/services/crypto.service';
import { ClipboardService } from '../../../core/services/clipboard.service';
import { PasswordGeneratorService } from '../../../core/services/password-generator.service';
import { VaultStore } from '../vault.store';
import { VaultItem, VaultCategory } from '../../../core/services/vault.service';

export interface CategoryMeta {
  id: VaultCategory | 'all';
  label: string;
  icon: string;
}

@Component({
  selector: 'app-vault-dashboard',
  standalone: true,
  imports: [
    CommonModule, RouterLink, ReactiveFormsModule, FormsModule,
    MatIconModule, MatTooltipModule, MatProgressSpinnerModule,
  ],
  providers: [VaultStore],
  templateUrl: './vault-dashboard.component.html',
  styles: [`
    .vault-bg { background: #080d1a; min-height: 100vh; }
    .vault-card {
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.07);
    }
    .vault-card:hover { border-color: rgba(6,182,212,0.25); }
    .vault-input {
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 0.75rem;
      color: white;
      width: 100%;
      padding: 0.75rem 1rem;
      font-size: 0.875rem;
      outline: none;
      transition: border-color 0.2s;
    }
    .vault-input:focus { border-color: #06b6d4; }
    .vault-input::placeholder { color: #4b5563; }
    .vault-btn-primary {
      background: linear-gradient(135deg, #06b6d4, #0284c7);
      color: white; border-radius: 0.75rem;
      padding: 0.75rem 1.5rem; font-weight: 700; font-size: 0.875rem;
      transition: all 0.2s;
    }
    .vault-btn-primary:hover:not(:disabled) {
      background: linear-gradient(135deg, #22d3ee, #0ea5e9);
      box-shadow: 0 0 20px rgba(6,182,212,0.3);
    }
    .vault-btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
    /* Fix autofill jaune Chrome */
    .vault-input:-webkit-autofill,
    .vault-input:-webkit-autofill:hover,
    .vault-input:-webkit-autofill:focus {
      -webkit-box-shadow: 0 0 0px 1000px #0f1729 inset !important;
      -webkit-text-fill-color: white !important;
      caret-color: white;
    }
    /* Modal */
    .vault-modal {
      background: #0f1729;
      border: 1px solid rgba(255,255,255,0.1);
      box-shadow: 0 25px 60px rgba(0,0,0,0.6);
    }
    /* Strength bar */
    .strength-bar { height: 3px; border-radius: 2px; transition: width 0.3s ease, background 0.3s ease; }
    /* Modal animation */
    @keyframes modal-in {
      from { opacity: 0; transform: scale(0.96) translateY(-8px); }
      to   { opacity: 1; transform: scale(1)    translateY(0);     }
    }
    .modal-animate { animation: modal-in 0.18s ease-out forwards; }
  `],
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

  readonly categories: CategoryMeta[] = [
    { id: 'all',   label: 'Tout',        icon: 'grid_view' },
    { id: 'login', label: 'Identifiants', icon: 'person' },
    { id: 'card',  label: 'Cartes',       icon: 'credit_card' },
    { id: 'note',  label: 'Notes',        icon: 'sticky_note_2' },
    { id: 'wifi',  label: 'Wi-Fi',        icon: 'wifi' },
    { id: 'other', label: 'Autre',        icon: 'more_horiz' },
  ];

  readonly categoryIcons: Record<string, string> = {
    login: 'person', card: 'credit_card', note: 'sticky_note_2', wifi: 'wifi', other: 'more_horiz',
  };

  searchQuery = '';
  activeCategory = signal<VaultCategory | 'all'>('all');

  readonly filteredItems$ = combineLatest([this.store.items$]).pipe(
    map(([items]) => items.filter(item => {
      const cat = this.activeCategory();
      const matchCat = cat === 'all' || item.category === cat;
      const q = this.searchQuery.toLowerCase();
      const matchQ = !q || item.title.toLowerCase().includes(q) || (item.username ?? '').toLowerCase().includes(q);
      return matchCat && matchQ;
    }))
  );

  readonly categoryCounts$ = this.store.items$.pipe(
    map(items => {
      const counts: Record<string, number> = { all: items.length };
      for (const item of items) counts[item.category] = (counts[item.category] ?? 0) + 1;
      return counts;
    })
  );

  get passwordStrength(): { width: string; color: string; label: string } {
    const pwd = this.form.controls.password_encrypted.value;
    if (!pwd) return { width: '0%', color: 'transparent', label: '' };
    let score = 0;
    if (pwd.length >= 8)  score++;
    if (pwd.length >= 16) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^A-Za-z0-9]/.test(pwd)) score++;
    if (score <= 1) return { width: '20%',  color: '#ef4444', label: 'Faible' };
    if (score <= 2) return { width: '40%',  color: '#f97316', label: 'Moyen' };
    if (score <= 3) return { width: '65%',  color: '#eab308', label: 'Bon' };
    if (score === 4) return { width: '85%',  color: '#22c55e', label: 'Fort' };
    return { width: '100%', color: '#06b6d4', label: 'Excellent' };
  }

  // Form state
  showForm = signal(false);
  editingItem = signal<VaultItem | null>(null);
  showPasswordInForm = signal(false);

  form = this.fb.nonNullable.group({
    title: ['', Validators.required],
    username: [''],
    password_encrypted: [''],
    url: [''],
    notes: [''],
    category: ['login' as VaultCategory],
    // Card-specific helpers (not sent directly to store)
    cardNumber: [''],
    cardCvv: [''],
    cardExpiry: [''],
  });

  revealedPasswords: Record<number, string | null> = {};
  copiedId: number | null = null;

  ngOnInit() {
    this.store.loadItems();
  }

  get formTitle() {
    return this.editingItem() ? 'Modifier l\'entrée' : 'Nouvelle entrée';
  }

  openCreate() {
    this.editingItem.set(null);
    this.form.reset({
      category: 'login', title: '', username: '', password_encrypted: '',
      url: '', notes: '', cardNumber: '', cardCvv: '', cardExpiry: '',
    });
    this.showPasswordInForm.set(false);
    this.showForm.set(true);
  }

  openEdit(item: VaultItem) {
    this.editingItem.set(item);
    this.form.patchValue({
      title: item.title,
      username: item.username ?? '',
      password_encrypted: '',
      url: item.url ?? '',
      notes: item.notes ?? '',
      category: item.category,
      cardNumber: '',
      cardCvv: '',
      cardExpiry: '',
    });
    this.showPasswordInForm.set(false);
    this.showForm.set(true);
  }

  closeForm() {
    this.showForm.set(false);
    this.editingItem.set(null);
  }

  generatePassword() {
    const pwd = this.passwordGenerator.generate(20);
    this.form.patchValue({ password_encrypted: pwd });
    this.showPasswordInForm.set(true);
  }

  submit() {
    const raw = this.form.getRawValue();
    const cat = raw.category;
    const editing = this.editingItem();

    // Build the secret field based on category
    let secret = raw.password_encrypted;
    if (cat === 'card') {
      if (raw.cardNumber || raw.cardCvv || raw.cardExpiry) {
        secret = JSON.stringify({ number: raw.cardNumber, cvv: raw.cardCvv, expiry: raw.cardExpiry });
      }
    } else if (cat === 'note') {
      secret = '';
    }

    // Validate create mode
    if (!editing) {
      if (!raw.title) return;
      if (cat === 'card' && !raw.cardNumber) return;
      if ((cat === 'login' || cat === 'wifi' || cat === 'other') && !secret) return;
    }

    const base = { title: raw.title, username: raw.username, url: raw.url, notes: raw.notes, category: cat };

    if (editing) {
      const payload: any = { id: editing.id, ...base };
      if (secret) payload.password_encrypted = secret;
      this.store.updateItem(payload);
      this.toast.success('Entrée mise à jour');
    } else {
      this.store.createItem({ ...base, password_encrypted: secret });
    }
    this.closeForm();
  }

  delete(id: number) {
    this.store.deleteItem(id);
    delete this.revealedPasswords[id];
  }

  async toggleReveal(item: VaultItem) {
    if (this.revealedPasswords[item.id] !== undefined) {
      delete this.revealedPasswords[item.id];
      return;
    }
    if (!item.password_encrypted) {
      this.revealedPasswords[item.id] = '';
      return;
    }
    try {
      this.revealedPasswords[item.id] = await this.cryptoService.decrypt(item.password_encrypted);
    } catch {
      this.revealedPasswords[item.id] = null;
      this.toast.error('Erreur de déchiffrement');
    }
  }

  async copyPassword(item: VaultItem) {
    if (!item.password_encrypted) { this.toast.warning('Aucun secret à copier'); return; }
    try {
      const plain = await this.cryptoService.decrypt(item.password_encrypted);
      let textToCopy = plain;
      if (item.category === 'card') {
        try { textToCopy = (JSON.parse(plain) as any).number ?? plain; } catch { /* use plain */ }
      }
      this.clipboardService.copy(textToCopy);
      this.copiedId = item.id;
      const msg = item.category === 'card'
        ? 'Numéro de carte copié — presse-papiers effacé dans 30s'
        : 'Mot de passe copié — presse-papiers effacé dans 30s';
      this.toast.success(msg);
      setTimeout(() => { if (this.copiedId === item.id) this.copiedId = null; }, 2000);
    } catch {
      this.toast.error('Erreur de déchiffrement');
    }
  }

  parseCardData(plain: string | null | undefined): { number: string; cvv: string; expiry: string } | null {
    if (!plain) return null;
    try {
      const obj = JSON.parse(plain) as { number?: string; cvv?: string; expiry?: string };
      if (obj.number !== undefined || obj.cvv !== undefined || obj.expiry !== undefined) return {
        number: obj.number ?? '', cvv: obj.cvv ?? '', expiry: obj.expiry ?? '',
      };
    } catch { /* not JSON */ }
    return null;
  }

  maskCardNumber(n: string): string {
    if (!n) return '•••• •••• •••• ••••';
    const clean = n.replace(/\s/g, '');
    return '•••• •••• •••• ' + (clean.length >= 4 ? clean.slice(-4) : clean);
  }

  isSubmitValid(): boolean {
    const raw = this.form.getRawValue();
    if (!raw.title) return false;
    const cat = raw.category;
    if (cat === 'card') return !!raw.cardNumber;
    if (cat === 'note') return true;
    return !!raw.password_encrypted;
  }

  async exportVault() {
    combineLatest([this.store.items$, this.store.loading$])
      .pipe(filter(([, loading]) => !loading), take(1), map(([items]) => items))
      .subscribe(async items => {
      const exportedAt = new Date().toISOString();
      const data = await Promise.all(items.map(async item => {
        let password: string | null = null;
        if (item.password_encrypted) {
          try { password = await this.cryptoService.decrypt(item.password_encrypted); }
          catch { password = null; }
        }
        return {
          title: item.title,
          username: item.username ?? null,
          password: password,
          url: item.url ?? null,
          notes: item.notes ?? null,
          category: item.category,
          exported_at: exportedAt,
        };
      }));
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cyber-vault-export-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      this.toast.success('Export téléchargé');
    });
  }

  logout() {
    this.authService.logout();
    this.cryptoService.clearKey();
    this.router.navigate(['/auth/login']);
  }
}
