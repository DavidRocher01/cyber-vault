import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

type ActionState = 'loading' | 'accepted' | 'rejected' | 'already' | 'error';

@Component({
  standalone: true,
  selector: 'app-quote-action',
  imports: [RouterLink, MatIconModule],
  templateUrl: './quote-action.component.html',
})
export class QuoteActionComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);

  state = signal<ActionState>('loading');
  action = signal<'accepter' | 'refuser'>('accepter');
  quoteNumber = signal('');
  errorMsg = signal('');

  ngOnInit() {
    const token = this.route.snapshot.paramMap.get('token') ?? '';
    const action = this.route.snapshot.url.at(-1)?.path as 'accepter' | 'refuser';
    this.action.set(action);

    const endpoint = action === 'accepter' ? 'accept' : 'reject';

    this.http
      .post<{
        status: string;
        quote_number: string;
        already: boolean;
      }>(`/api/v1/quotes/${token}/${endpoint}`, {})
      .subscribe({
        next: res => {
          this.quoteNumber.set(res.quote_number);
          if (res.already) {
            this.state.set('already');
          } else {
            this.state.set(res.status as ActionState);
          }
        },
        error: err => {
          this.errorMsg.set(err.error?.detail ?? 'Une erreur est survenue.');
          this.state.set('error');
        },
      });
  }
}
