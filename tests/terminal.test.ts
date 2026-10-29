import { expect, test } from 'bun:test';

for (const exit of ['exit', 'quit', '\\q']) {
  test(`REPL executes multiple queries and stops at ${exit}`, async () => {
    const proc = Bun.spawn(['bun', 'run', 'src/cli.ts'], {
      stdin: new Blob([`\nWHAT_IF COMMIT;\nSELECT student_id FROM students;\n${exit}\nSHOULD_NOT_RUN\n`]),
      stdout: 'pipe', stderr: 'pipe',
      env: { ...process.env, WHATIF_API_URL: 'http://127.0.0.1:1/api/whatif' },
    });
    const output = await new Response(proc.stdout).text();
    expect(await proc.exited).toBe(0);
    expect(output).toContain('INTERACTIVE REPL');
    expect(output.match(/whatif> /g)!.length).toBeGreaterThanOrEqual(3);
    expect(output).toContain('COMMIT');
    expect(output).toContain('SELECT student_id FROM students');
    expect(output).toContain('SELECT result');
    expect(output).not.toContain('SHOULD_NOT_RUN');
  });
}

test('REPL exits cleanly on EOF', async () => {
  const proc = Bun.spawn(['bun', 'run', 'src/cli.ts'], { stdin: new Blob([]), stdout: 'pipe', stderr: 'pipe' });
  expect(await proc.exited).toBe(0);
  expect(await new Response(proc.stdout).text()).toContain('whatif> ');
});
