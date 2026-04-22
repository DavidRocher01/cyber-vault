import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NotFoundComponent } from './not-found.component';

function makeInstance(): NotFoundComponent {
  const cdrMock = { markForCheck: vi.fn() };
  const comp = new NotFoundComponent(cdrMock as any);
  return comp;
}

function outputLines(comp: NotFoundComponent): string[] {
  return comp.termLines.filter(l => !l.isCmd).map(l => l.text);
}

describe('NotFoundComponent — initial state', () => {
  it('starts with termOpen false', () => {
    const comp = makeInstance();
    expect(comp.termOpen).toBe(false);
  });

  it('starts with two welcome lines', () => {
    const comp = makeInstance();
    expect(comp.termLines).toHaveLength(2);
    expect(comp.termLines[0].isCmd).toBe(false);
  });
});

describe('NotFoundComponent — termSubmit()', () => {
  let comp: NotFoundComponent;

  beforeEach(() => { comp = makeInstance(); });

  it('ignores empty input', () => {
    const before = comp.termLines.length;
    comp.termCurrent = '   ';
    comp.termSubmit();
    expect(comp.termLines).toHaveLength(before);
  });

  it('pushes the command as a cmd line', () => {
    comp.termCurrent = 'help';
    comp.termSubmit();
    const cmdLines = comp.termLines.filter(l => l.isCmd);
    expect(cmdLines[0].text).toBe('$ help');
  });

  it('help — responds with available commands list', () => {
    comp.termCurrent = 'help';
    comp.termSubmit();
    const out = outputLines(comp).join('\n');
    expect(out).toContain('scan');
    expect(out).toContain('ping');
  });

  it('whoami — responds with access denied message', () => {
    comp.termCurrent = 'whoami';
    comp.termSubmit();
    const out = outputLines(comp).join('\n');
    expect(out).toContain('accès refusé');
  });

  it('ping — responds with timeout message', () => {
    comp.termCurrent = 'ping';
    comp.termSubmit();
    const out = outputLines(comp).join('\n');
    expect(out).toContain('Request timeout');
  });

  it('trace — responds with unreachable trace output', () => {
    comp.termCurrent = 'trace';
    comp.termSubmit();
    const out = outputLines(comp).join('\n');
    expect(out).toContain('Destination unreachable');
  });

  it('hint — reveals the /cyberscan/r00t path', () => {
    comp.termCurrent = 'hint';
    comp.termSubmit();
    const out = outputLines(comp).join('\n');
    expect(out).toContain('/cyberscan/r00t');
  });

  it('scan — outputs 404 error code', () => {
    comp.termCurrent = 'scan';
    comp.termSubmit();
    const out = outputLines(comp).join('\n');
    expect(out).toContain('0x404');
  });

  it('unknown command — outputs "command not found"', () => {
    comp.termCurrent = 'foobar';
    comp.termSubmit();
    const out = outputLines(comp).join('\n');
    expect(out).toContain('command not found');
  });

  it('clear — empties termLines', () => {
    comp.termCurrent = 'help';
    comp.termSubmit();
    comp.termCurrent = 'clear';
    comp.termSubmit();
    expect(comp.termLines).toHaveLength(0);
  });

  it('clears termCurrent after submit', () => {
    comp.termCurrent = 'ping';
    comp.termSubmit();
    expect(comp.termCurrent).toBe('');
  });

  it('is case-insensitive — HELP resolves same as help', () => {
    comp.termCurrent = 'HELP';
    comp.termSubmit();
    const out = outputLines(comp).join('\n');
    expect(out).toContain('scan');
  });

  it('calls cdr.markForCheck() after each submit', () => {
    comp.termCurrent = 'whoami';
    comp.termSubmit();
    expect((comp as any).cdr.markForCheck).toHaveBeenCalled();
  });
});
