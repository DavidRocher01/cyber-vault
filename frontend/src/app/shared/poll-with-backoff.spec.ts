/**
 * pollWithBackoff — tests de non-régression.
 *
 * Vérifie que le helper de polling avec backoff exponentiel :
 *  - appelle le fetcher à chaque tick
 *  - complète l'observable quand isDone retourne true
 *  - émet la valeur finale avant de compléter (inclusive takeWhile)
 *  - double le délai à chaque tick jusqu'au cap maxMs
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { of, lastValueFrom, firstValueFrom, toArray } from 'rxjs';
import { pollWithBackoff } from './poll-with-backoff';

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); });

describe('pollWithBackoff — comportement de base', () => {

  it('appelle le fetcher et émet sa valeur', async () => {
    const fetcher = vi.fn(() => of({ status: 'done' }));
    const promise = firstValueFrom(
      pollWithBackoff(fetcher, v => v.status === 'done')
    );
    await vi.runAllTimersAsync();
    const result = await promise;
    expect(fetcher).toHaveBeenCalled();
    expect(result).toEqual({ status: 'done' });
  });

  it('complète dès que isDone retourne true', async () => {
    let call = 0;
    const fetcher = vi.fn(() => of({ status: call++ === 0 ? 'pending' : 'done' }));
    const results: any[] = [];

    const sub = pollWithBackoff(fetcher, v => v.status === 'done').subscribe({
      next: v => results.push(v),
    });

    await vi.runAllTimersAsync();
    sub.unsubscribe();

    // Doit avoir complété avec au moins une valeur 'done'
    expect(results.some(r => r.status === 'done')).toBe(true);
  });

  it('émet la valeur finale (done) avant de compléter — inclusive takeWhile', async () => {
    const fetcher = vi.fn(() => of({ status: 'done' }));
    const results: any[] = [];

    const promise = lastValueFrom(
      pollWithBackoff(fetcher, v => v.status === 'done').pipe(toArray())
    );
    await vi.runAllTimersAsync();
    const all = await promise;

    // La valeur done doit être émise (pas juste ignorée)
    expect(all.length).toBeGreaterThanOrEqual(1);
    expect(all[all.length - 1]).toEqual({ status: 'done' });
  });

  it('ne complète pas si isDone retourne toujours false', async () => {
    const fetcher = vi.fn(() => of({ status: 'pending' }));
    const results: any[] = [];
    let completed = false;

    const sub = pollWithBackoff(
      fetcher,
      () => false,
      100,   // initialMs court pour le test
      200,   // maxMs
    ).subscribe({
      next: v => results.push(v),
      complete: () => { completed = true; },
    });

    // Avancer de 500ms — plusieurs ticks
    await vi.advanceTimersByTimeAsync(500);
    sub.unsubscribe();

    expect(completed).toBe(false);
    expect(results.length).toBeGreaterThan(0);
  });

});

describe('pollWithBackoff — backoff exponentiel', () => {

  it('démarre avec le délai initialMs', async () => {
    const fetcher = vi.fn(() => of({ status: 'pending' }));
    const sub = pollWithBackoff(fetcher, () => false, 1000, 10000).subscribe();

    // Avant 1000ms : pas encore appelé
    await vi.advanceTimersByTimeAsync(999);
    expect(fetcher).not.toHaveBeenCalled();

    // À 1000ms : premier appel
    await vi.advanceTimersByTimeAsync(1);
    expect(fetcher).toHaveBeenCalledTimes(1);

    sub.unsubscribe();
  });

  it('double le délai au deuxième tick', async () => {
    const fetcher = vi.fn(() => of({ status: 'pending' }));
    const sub = pollWithBackoff(fetcher, () => false, 1000, 10000).subscribe();

    await vi.advanceTimersByTimeAsync(1000); // tick 1 à t=1000
    expect(fetcher).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1999); // pas encore le tick 2
    expect(fetcher).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1); // tick 2 à t=3000 (1000 + 2000)
    expect(fetcher).toHaveBeenCalledTimes(2);

    sub.unsubscribe();
  });

  it('plafonne le délai à maxMs', async () => {
    const fetcher = vi.fn(() => of({ status: 'pending' }));
    const sub = pollWithBackoff(fetcher, () => false, 1000, 2000).subscribe();

    // tick 1: t=1000, tick 2: t=1000+2000=3000, tick 3: t=3000+2000=5000 (plafonné à 2000)
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetcher).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(2000);
    expect(fetcher).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(2000); // doit être 2000, pas 4000
    expect(fetcher).toHaveBeenCalledTimes(3);

    sub.unsubscribe();
  });

});
