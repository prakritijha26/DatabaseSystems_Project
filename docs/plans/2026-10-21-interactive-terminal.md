# Interactive terminal implementation

User-approved scope: replace the scenario UI with a manual SQL shell and provide a persistent Bun CLI prompt. Work in the requested checkout and leave Git operations to the user.

1. web/index.html and web/style.css: remove track controls/styles, add the terminal title, prompt, keyboard help and collapsible schema reference with primary keys. Keep report panels. Low risk; independent.
2. src/app.ts: remove scenario imports/listeners; implement history with draft restoration, editor auto-sizing, Enter execution and Shift+Enter multiline editing. Retain backend rendering and truthful rollback state. Medium risk; depends on step 1.
3. src/cli.ts: use readline for a sequential prompt loop, exit commands and EOF; retain argument mode and print SELECT tables. Medium risk; independent.
4. Verify REPL behavior before/after implementation, browser keyboard behavior, requested Python suites, demos and Bun build. Review source changes for correctness and input handling; regenerate web/app.js after any frontend edit.

No backend/API/schema changes. Existing offline fixtures and PostgreSQL limitations remain as recorded in docs/debt. Rollback confirmation is conditional on actual engine evidence; physical disk immutability is not asserted.
