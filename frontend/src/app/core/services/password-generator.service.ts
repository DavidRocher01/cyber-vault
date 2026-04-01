import { Injectable } from '@angular/core';

const CHARSET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?';

@Injectable({ providedIn: 'root' })
export class PasswordGeneratorService {
  generate(length = 16): string {
    const array = crypto.getRandomValues(new Uint32Array(length));
    return Array.from(array, x => CHARSET[x % CHARSET.length]).join('');
  }
}
