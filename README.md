# migsafe

This migration would have locked your users table for 40 seconds. migsafe tells you before it merges.

```bash
migsafe check migrations/
```

```
migsafe: 4 finding(s), worst critical

[CRITICAL] line 7 (drop-table)
  what: DROP TABLE destroys data and cannot be undone by rollback after commit
  fix:  Rename the table instead, drop it in a later release once nothing references it

[CRITICAL] line 8 (unbounded-write)
  what: UPDATE without WHERE touches every row and locks them
  fix:  Add a WHERE clause and batch the operation

[HIGH] line 6 (volatile-default)
  what: Volatile DEFAULT (now()) rewrites the table and takes a long lock
  fix:  Add the column without a default, backfill in batches, then set the default

[MEDIUM] line 1 (no-timeout)
  what: Migration sets no statement_timeout or lock_timeout
  fix:  Prefix the migration with SET lock_timeout = '3s'; SET statement_timeout = '30s'
```

## Install

```bash
pipx install migsafe
```

Python 3.9+, no dependencies, no database connection. It reads SQL files.

## Usage

```bash
migsafe check migrations/                     # a directory of .sql files
migsafe check 001_init.sql 002_add_users.sql  # specific files
migsafe check migrations/ --json              # for CI and agents
migsafe check migrations/ --fail-on critical  # exit 2 only on data loss
```

Default exit behaviour: **2 when any finding is high or critical**, 0 otherwise. Wire it into CI
next to your migration runner.

```yaml
- name: Migration safety
  run: migsafe check migrations/
```

## Rules

| Rule | Severity | Why it matters |
|---|---|---|
| `drop-table` | critical | data is gone after commit; rollback does not restore it |
| `drop-column` | critical | same, one column at a time |
| `truncate` | critical | ACCESS EXCLUSIVE lock plus total data loss |
| `unbounded-write` | critical | `UPDATE`/`DELETE` with no `WHERE` locks and rewrites every row |
| `index-not-concurrent` | high | a plain `CREATE INDEX` blocks writes for the whole build |
| `add-not-null-column` | high | fails outright on a non-empty table |
| `volatile-default` | high | `DEFAULT now()` style defaults rewrite the table |
| `alter-column-type` | high | type changes rewrite the table under an exclusive lock |
| `constraint-without-not-valid` | high | `ADD CONSTRAINT` validates every row while holding a lock |
| `unbatched-backfill` | medium | one giant `UPDATE` holds one giant transaction |
| `multiple-alter-ops` | medium | combined ALTERs hold locks for the slowest operation |
| `rename` | medium | renames break code still running during the deploy |
| `set-not-null` | medium | full scan under an exclusive lock |
| `no-timeout` | medium | no `lock_timeout`, so a blocked migration waits forever |

## What it understands

- Statements are split on top-level semicolons. Semicolons inside strings, `--` comments, `/* */`
  blocks, and `$$`-quoted function bodies are ignored.
- `CREATE INDEX` on a table **created in the same migration** is not flagged, because there are no
  readers to block.
- `SET lock_timeout` / `SET statement_timeout` anywhere in the file satisfies `no-timeout`.

## Honest limits

- PostgreSQL only. MySQL and SQLite have different locking rules and are not modelled.
- It is a static pattern matcher, not a query planner. A migration that passes can still be slow.
- It cannot see table sizes, so severity is by shape, not by measured impact.
- "No issues found" is the absence of known dangerous shapes. It is never a guarantee.

## How it works

1. Read the file, strip comments while preserving line numbers.
2. Split into statements, respecting quotes and dollar-quoted blocks.
3. Collect tables created in the migration set.
4. Apply the rule table above, skipping rules that do not apply (new tables, `CONCURRENTLY`,
   `NOT VALID`).
5. Sort by severity then line, render text or JSON, set the exit code.

## Tests

```bash
python -m pytest -q
```

Fourteen tests: each rule fires, each escape hatch suppresses it, parser edge cases
(semicolons in strings and comments, dollar-quoted bodies), and a clean migration.

## Contributing

New rules need a firing fixture and a suppressing one. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
