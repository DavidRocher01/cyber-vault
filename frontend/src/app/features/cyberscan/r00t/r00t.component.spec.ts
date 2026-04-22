import { describe, it, expect, vi, beforeEach } from 'vitest';
import { R00tComponent } from './r00t.component';

interface Line { type: 'cmd' | 'out' | 'err'; text: string; }

function makeInstance(): R00tComponent {
  const routerMock = { navigate: vi.fn() };
  const cdrMock = { markForCheck: vi.fn() };

  const comp = Object.create(R00tComponent.prototype) as R00tComponent;
  (comp as any).router = routerMock;
  (comp as any).cdr = cdrMock;
  comp.lines = [];
  comp.currentInput = '';
  comp.prompt = 'r00t@cyberscan-edge-07:~$ ';
  (comp as any).history = [];
  (comp as any).historyIdx = -1;
  return comp;
}

function linesOfType(comp: R00tComponent, type: 'out' | 'err'): string[] {
  return comp.lines.filter((l: Line) => l.type === type).map((l: Line) => l.text);
}

describe('R00tComponent — execute() commands', () => {
  let comp: R00tComponent;

  beforeEach(() => { comp = makeInstance(); });

  it('help — outputs "Available commands:" header', () => {
    (comp as any).execute('help');
    expect(linesOfType(comp, 'out')[0]).toBe('Available commands:');
  });

  it('whoami — outputs "r00t"', () => {
    (comp as any).execute('whoami');
    expect(linesOfType(comp, 'out')).toContain('r00t');
  });

  it('uname — outputs Linux kernel string', () => {
    (comp as any).execute('uname');
    const out = linesOfType(comp, 'out');
    expect(out[0]).toContain('Linux cyberscan-edge-07');
  });

  it('date — outputs a non-empty date string', () => {
    (comp as any).execute('date');
    const out = linesOfType(comp, 'out');
    expect(out[0].length).toBeGreaterThan(0);
  });

  it('ls — lists all expected filenames', () => {
    (comp as any).execute('ls');
    const out = linesOfType(comp, 'out').join('');
    expect(out).toContain('audit.log');
    expect(out).toContain('.secrets');
    expect(out).toContain('config.yml');
  });

  it('ps — includes PID header and cyberscan-scanner process', () => {
    (comp as any).execute('ps');
    const out = linesOfType(comp, 'out').join('\n');
    expect(out).toContain('PID');
    expect(out).toContain('cyberscan-scanner');
  });

  it('nmap — outputs port scan results', () => {
    (comp as any).execute('nmap');
    const out = linesOfType(comp, 'out').join('\n');
    expect(out).toContain('443/tcp');
    expect(out).toContain('Nmap done');
  });

  it('clear — empties lines array', () => {
    comp.lines = [{ type: 'out', text: 'hello' }, { type: 'cmd', text: 'ls' }];
    (comp as any).execute('clear');
    expect(comp.lines).toHaveLength(0);
  });

  it('unknown command — outputs "command not found" error', () => {
    (comp as any).execute('foobar');
    const err = linesOfType(comp, 'err');
    expect(err[0]).toContain('foobar: command not found');
  });

  it('exit — calls router.navigate with ["/cyberscan"]', () => {
    (comp as any).execute('exit');
    expect((comp as any).router.navigate).toHaveBeenCalledWith(['/cyberscan']);
  });
});

describe('R00tComponent — catFile()', () => {
  let comp: R00tComponent;

  beforeEach(() => { comp = makeInstance(); });

  it('no argument — outputs "missing operand" error', () => {
    (comp as any).catFile(undefined);
    expect(linesOfType(comp, 'err')[0]).toContain('missing operand');
  });

  it('.secrets — outputs "Permission denied" error', () => {
    (comp as any).catFile('.secrets');
    const err = linesOfType(comp, 'err');
    expect(err[0]).toContain('Permission denied');
  });

  it('.secrets — includes easter egg hint line', () => {
    (comp as any).catFile('.secrets');
    const err = linesOfType(comp, 'err');
    expect(err[1]).toContain('aussi facile');
  });

  it('unknown file — outputs "No such file or directory"', () => {
    (comp as any).catFile('ghost.txt');
    expect(linesOfType(comp, 'err')[0]).toContain('No such file or directory');
  });

  it('audit.log — outputs log lines with timestamps', () => {
    (comp as any).catFile('audit.log');
    const out = linesOfType(comp, 'out').join('\n');
    expect(out).toContain('[2026-04-20');
    expect(out).toContain('scan complete');
  });

  it('config.yml — outputs YAML content', () => {
    (comp as any).catFile('config.yml');
    const out = linesOfType(comp, 'out').join('\n');
    expect(out).toContain('scanner:');
    expect(out).toContain('workers:');
  });

  it('binary file (vuln_db.sqlite) — outputs binary data message', () => {
    (comp as any).catFile('vuln_db.sqlite');
    const out = linesOfType(comp, 'out')[0];
    expect(out).toContain('[binary data');
  });
});

describe('R00tComponent — history navigation', () => {
  let comp: R00tComponent;

  beforeEach(() => { comp = makeInstance(); });

  it('historyPrev does nothing when history is empty', () => {
    comp.historyPrev();
    expect(comp.currentInput).toBe('');
  });

  it('historyPrev sets currentInput to last command', () => {
    (comp as any).history = ['ls', 'whoami'];
    comp.historyPrev();
    expect(comp.currentInput).toBe('ls');
  });

  it('historyPrev clamps at oldest entry', () => {
    (comp as any).history = ['ls', 'whoami'];
    comp.historyPrev();
    comp.historyPrev();
    comp.historyPrev(); // should not go beyond
    expect(comp.currentInput).toBe('whoami');
  });

  it('historyNext clears input when at index -1', () => {
    comp.currentInput = 'something';
    (comp as any).historyIdx = -1;
    comp.historyNext();
    expect(comp.currentInput).toBe('');
  });

  it('historyNext navigates forward after historyPrev', () => {
    (comp as any).history = ['ls', 'whoami'];
    comp.historyPrev(); // idx=0 → 'ls'
    comp.historyPrev(); // idx=1 → 'whoami'
    comp.historyNext(); // idx=0 → 'ls'
    expect(comp.currentInput).toBe('ls');
  });
});

describe('R00tComponent — autocomplete()', () => {
  let comp: R00tComponent;

  beforeEach(() => { comp = makeInstance(); });

  it('completes a partial command', () => {
    comp.currentInput = 'wh';
    comp.autocomplete();
    expect(comp.currentInput).toBe('whoami');
  });

  it('does nothing for exact match', () => {
    comp.currentInput = 'help';
    comp.autocomplete();
    expect(comp.currentInput).toBe('help');
  });

  it('does nothing for unknown prefix', () => {
    comp.currentInput = 'xyz';
    comp.autocomplete();
    expect(comp.currentInput).toBe('xyz');
  });
});

describe('R00tComponent — submit()', () => {
  let comp: R00tComponent;

  beforeEach(() => {
    vi.useFakeTimers();
    comp = makeInstance();
    (comp as any).scrollBottom = vi.fn();
  });

  afterEach(() => { vi.useRealTimers(); });

  it('ignores empty input', () => {
    comp.currentInput = '   ';
    comp.submit();
    expect(comp.lines).toHaveLength(0);
  });

  it('adds command to history', () => {
    comp.currentInput = 'ls';
    comp.submit();
    expect((comp as any).history[0]).toBe('ls');
  });

  it('resets historyIdx to -1', () => {
    (comp as any).historyIdx = 3;
    comp.currentInput = 'whoami';
    comp.submit();
    expect((comp as any).historyIdx).toBe(-1);
  });

  it('clears currentInput after submit', () => {
    comp.currentInput = 'help';
    comp.submit();
    expect(comp.currentInput).toBe('');
  });
});
