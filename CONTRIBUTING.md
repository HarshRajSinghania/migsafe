# Contributing

## Most useful contributions

1. **A new rule** for a Postgres lock or data-loss shape we miss. Add it to `check_statement`,
   with a severity, a fix, a firing test, and a suppressing test.
2. **Migration-runner integration** (Alembic, Flyway, Django, Atlas) so migsafe can be called from
   the runner rather than CI.
3. **Dialect notes** for MySQL or SQLite, as documentation first, code second.

## Rules

- No database connection. migsafe reads files and must stay usable in CI with no credentials.
- Every rule needs both a fire case and an escape hatch case.
- Severity is about consequence: data loss is critical even if the table is small.
- Never say a migration is safe. Say which rules fired and which did not apply.

## Tests

```bash
python -m pytest -q
```
