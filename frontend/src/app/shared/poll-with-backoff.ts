/**
 * Creates an Observable that polls by calling `fetcher()` with exponential backoff.
 * Starts at `initialMs`, doubles each tick, capped at `maxMs`.
 * Completes when `isDone` returns true (inclusive: emits the final value before completing).
 *
 * Usage:
 *   pollWithBackoff(() => this.service.getScan(id), s => s.status === 'done')
 *     .subscribe(scan => this.scan.set(scan));
 */
import { Observable, switchMap, takeWhile, timer } from 'rxjs';
import { scan as rxScan } from 'rxjs/operators';

export function pollWithBackoff<T>(
  fetcher: () => Observable<T>,
  isDone: (value: T) => boolean,
  initialMs = 3_000,
  maxMs = 30_000,
): Observable<T> {
  // Emit tick index: 0, 1, 2, ...
  const ticks$ = new Observable<number>(observer => {
    let index = 0;
    let timeoutId: ReturnType<typeof setTimeout>;

    const schedule = () => {
      const delay = Math.min(initialMs * Math.pow(2, index), maxMs);
      timeoutId = setTimeout(() => {
        observer.next(index++);
        schedule();
      }, delay);
    };

    schedule();
    return () => clearTimeout(timeoutId);
  });

  return ticks$.pipe(
    switchMap(() => fetcher()),
    takeWhile(value => !isDone(value), true),
  );
}
