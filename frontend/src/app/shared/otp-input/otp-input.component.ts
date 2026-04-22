import { Component, EventEmitter, Input, Output, QueryList, ViewChildren, ElementRef, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    standalone: true,
    selector: 'app-otp-input',
    imports: [CommonModule],
    template: `
    <div class="flex gap-2 justify-center">
      @for (i of indices; track i) {
        <input
          #otpInput
          type="text"
          inputmode="numeric"
          maxlength="1"
          [value]="digits[i]"
          (input)="onInput($event, i)"
          (keydown)="onKeydown($event, i)"
          (paste)="onPaste($event)"
          (focus)="onFocus($event)"
          autocomplete="one-time-code"
          class="w-11 h-14 text-center text-2xl font-mono font-bold text-white rounded-xl border bg-white/4 outline-none transition-all caret-transparent select-all"
          [class.border-gray-700]="!digits[i]"
          [class.border-cyan-500]="!!digits[i]"
          [class.shadow-otp-active]="!!digits[i]"
          style="background:rgba(255,255,255,.04)"
        />
      }
    </div>
  `,
    styles: [`
    input:focus {
      border-color: #22d3ee !important;
      box-shadow: 0 0 0 3px rgba(34,211,238,.15);
    }
    .shadow-otp-active {
      box-shadow: 0 0 0 1px rgba(34,211,238,.2);
    }
  `]
})
export class OtpInputComponent implements OnChanges {
  /** Set to true to clear and refocus the component */
  @Input() clearTrigger = 0;
  @Output() codeChange = new EventEmitter<string>();
  /** Emitted when all 6 digits are filled */
  @Output() otpComplete = new EventEmitter<string>();

  @ViewChildren('otpInput') inputs!: QueryList<ElementRef<HTMLInputElement>>;

  readonly indices = [0, 1, 2, 3, 4, 5];
  digits: string[] = ['', '', '', '', '', ''];

  ngOnChanges(changes: SimpleChanges) {
    if (changes['clearTrigger'] && !changes['clearTrigger'].firstChange) {
      this.clear();
    }
  }

  onInput(event: Event, index: number) {
    const input = event.target as HTMLInputElement;
    const value = input.value.replace(/\D/g, '').slice(-1);
    this.digits = [...this.digits];
    this.digits[index] = value;
    input.value = value;
    if (value && index < 5) this.focusAt(index + 1);
    this.emit();
  }

  onKeydown(event: KeyboardEvent, index: number) {
    if (event.key === 'Backspace') {
      this.digits = [...this.digits];
      if (this.digits[index]) {
        this.digits[index] = '';
      } else if (index > 0) {
        this.digits[index - 1] = '';
        this.focusAt(index - 1);
      }
      this.emit();
    } else if (event.key === 'ArrowLeft' && index > 0) {
      this.focusAt(index - 1);
    } else if (event.key === 'ArrowRight' && index < 5) {
      this.focusAt(index + 1);
    }
  }

  onPaste(event: ClipboardEvent) {
    event.preventDefault();
    const text = (event.clipboardData?.getData('text') ?? '').replace(/\D/g, '').slice(0, 6);
    this.digits = Array(6).fill('').map((_, i) => text[i] ?? '');
    const nextEmpty = this.digits.findIndex(d => !d);
    this.focusAt(nextEmpty === -1 ? 5 : nextEmpty);
    this.emit();
  }

  onFocus(event: Event) {
    setTimeout(() => (event.target as HTMLInputElement).select(), 0);
  }

  private focusAt(index: number) {
    setTimeout(() => this.inputs.get(index)?.nativeElement.focus(), 0);
  }

  private emit() {
    const code = this.digits.join('');
    this.codeChange.emit(code);
    if (code.length === 6 && !this.digits.includes('')) {
      this.otpComplete.emit(code);
    }
  }

  clear() {
    this.digits = ['', '', '', '', '', ''];
    setTimeout(() => this.focusAt(0), 50);
  }

  get code(): string {
    return this.digits.join('');
  }
}
