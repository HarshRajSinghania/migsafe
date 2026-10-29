# Contributing

## Adding a rule

Rules live in `migsafe/rules.py`. Each one needs:

- an `id` (stable, kebab-case)
- a severity from `SEVERITY_ORDER`
- a `what` sentence describing the production consequence, not the SQL keyword
- a `fix` sentence a developer can act on

Add a case to `tests/test_rules.py` with the smallest SQL that triggers it, plus a **negative** test
proving the nearby safe form is not flagged. A rule that cannot distinguish the safe form is not
ready.

## Running the tests

```bash
python -m pytest -q
```

## Rules of the road

- PostgreSQL first. Other dialects are a separate module, not a regex tweak.
- Never flag a table created in the same file (see `new-table` suppression).
- Explain the consequence: "blocks writes for the whole build", not "concurrent=false".
- Critical means "irreversible or takes the table down". Do not inflate severity.
- No database connection, ever. This is static analysis of the SQL you are about to run.

## Pull requests

One rule per PR, positive and negative test, `pytest` green.
