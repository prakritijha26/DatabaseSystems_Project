import { expect, test } from 'bun:test';
import { formatReport } from '../src/cli';
import type { ImpactReport } from '../src/types';

function output(backend: string) {
  const lines: string[] = [];
  const original = console.log;
  console.log = (...args) => { lines.push(args.join(' ')); };
  try {
    formatReport({ statement: 'APPLY UPDATE marks SET score=50;', status: 'COMMITTED',
      statement_type: 'DML', engine_backend: backend, committed: true, rolled_back: false,
      execution_time_ms: 1, tables_affected: [], metrics: [], broken_dependencies: [], logs: [] } as ImpactReport);
  } finally { console.log = original; }
  return lines.join('\n');
}
test('live commits display permanent commit instead of rollback', () => {
  expect(output('live')).toContain('[COMMITTED / PERMANENT]');
  expect(output('live')).toContain('Permanent commit confirmed by PostgreSQL');
  expect(output('live')).not.toContain('Rollback not confirmed');
});
test('offline acknowledgements never display permanent PostgreSQL confirmation', () => {
  expect(output('mock')).toContain('[OFFLINE FIXTURE]');
  expect(output('mock')).not.toContain('Permanent commit confirmed');
});

import { executeQuery } from '../src/cli';
import { spyOn } from 'bun:test';

test('permanent HTTP failure never replays the mutation through Python', async () => {
  const original = globalThis.fetch;
  const spawn = spyOn(Bun, 'spawn');
  try {
    for (const sql of ['APPLY UPDATE marks SET score=50;', 'RESEED;', 'RESET;']) {
      globalThis.fetch = (async () => new Response('server failed', {status: 500})) as typeof fetch;
      await expect(executeQuery(sql)).rejects.toThrow('not retried');
      globalThis.fetch = (async () => { throw new Error('connection lost after delivery'); }) as typeof fetch;
      await expect(executeQuery(sql)).rejects.toThrow('not retried');
    }
    expect(spawn).not.toHaveBeenCalled();
  } finally {
    globalThis.fetch = original;
    spawn.mockRestore();
  }
});
