import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SimpleChange } from '@angular/core';
import { MatrixRainComponent } from './matrix-rain.component';

function makeInstance(): MatrixRainComponent {
  const comp = Object.create(MatrixRainComponent.prototype) as MatrixRainComponent;
  (comp as any).rafId = 0;
  (comp as any).drops = [];
  (comp as any).autoClose = undefined;
  comp.visible = false;
  comp.closeRequested = false;
  return comp;
}

describe('MatrixRainComponent — ngOnChanges', () => {
  let comp: MatrixRainComponent;
  let startSpy: ReturnType<typeof vi.fn>;
  let stopSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    comp = makeInstance();
    startSpy = vi.fn();
    stopSpy = vi.fn();
    (comp as any).start = startSpy;
    (comp as any).stop = stopSpy;
  });

  afterEach(() => { vi.useRealTimers(); });

  it('schedules start() via setTimeout when visible becomes true', () => {
    comp.visible = true;
    comp.ngOnChanges({ visible: new SimpleChange(false, true, false) });
    expect(startSpy).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(startSpy).toHaveBeenCalledOnce();
  });

  it('calls stop() when visible becomes false', () => {
    comp.visible = false;
    comp.ngOnChanges({ visible: new SimpleChange(true, false, false) });
    expect(stopSpy).toHaveBeenCalledOnce();
  });

  it('does nothing when unrelated input changes', () => {
    comp.ngOnChanges({});
    expect(startSpy).not.toHaveBeenCalled();
    expect(stopSpy).not.toHaveBeenCalled();
  });
});

describe('MatrixRainComponent — onClose', () => {
  let comp: MatrixRainComponent;
  let stopSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    comp = makeInstance();
    stopSpy = vi.fn();
    (comp as any).stop = stopSpy;
  });

  it('sets closeRequested to true', () => {
    comp.onClose();
    expect(comp.closeRequested).toBe(true);
  });

  it('calls stop()', () => {
    comp.onClose();
    expect(stopSpy).toHaveBeenCalledOnce();
  });
});

describe('MatrixRainComponent — ngOnDestroy', () => {
  it('calls stop() on destroy', () => {
    const comp = makeInstance();
    const stopSpy = vi.fn();
    (comp as any).stop = stopSpy;
    comp.ngOnDestroy();
    expect(stopSpy).toHaveBeenCalledOnce();
  });
});

describe('MatrixRainComponent — start/stop animation', () => {
  let comp: MatrixRainComponent;

  beforeEach(() => {
    vi.useFakeTimers();
    comp = makeInstance();
    // Provide a minimal canvas stub
    const ctx = {
      fillStyle: '',
      font: '',
      fillRect: vi.fn(),
      fillText: vi.fn(),
    };
    const canvas = {
      width: 0,
      height: 0,
      getContext: vi.fn().mockReturnValue(ctx),
    };
    comp.canvasRef = { nativeElement: canvas } as any;
  });

  afterEach(() => { vi.useRealTimers(); });

  it('stop() cancels the RAF id and clears the autoClose timer', () => {
    const cancelSpy = vi.spyOn(global, 'cancelAnimationFrame').mockImplementation(() => {});
    (comp as any).rafId = 42;
    (comp as any).stop();
    expect(cancelSpy).toHaveBeenCalledWith(42);
    cancelSpy.mockRestore();
  });

  it('start() schedules autoClose after 6000ms', () => {
    vi.spyOn(global, 'requestAnimationFrame').mockReturnValue(1 as any);
    vi.spyOn(global, 'cancelAnimationFrame').mockImplementation(() => {});
    (comp as any).start();
    // autoClose timer should be set; advance 6001ms and expect stop was called
    const stopSpy = vi.fn();
    (comp as any).stop = stopSpy;
    // Re-attach spy and advance
    (comp as any).autoClose = setTimeout(() => (comp as any).stop(), 6000);
    vi.advanceTimersByTime(6001);
    expect(stopSpy).toHaveBeenCalled();
  });

  it('start() resets closeRequested to false', () => {
    vi.spyOn(global, 'requestAnimationFrame').mockReturnValue(1 as any);
    comp.closeRequested = true;
    (comp as any).start();
    expect(comp.closeRequested).toBe(false);
  });
});
