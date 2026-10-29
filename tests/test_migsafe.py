"""Tests for migsafe rules."""

from migsafe.parse import split_statements
from migsafe.rules import check_sql


def rules_for(sql: str) -> set[str]:
    return {f.rule for f in check_sql(sql).findings}


def test_parser_keeps_dollar_quoted_body_whole():
    sql = "CREATE FUNCTION f() RETURNS void AS $$ BEGIN PERFORM 1; END $$ LANGUAGE plpgsql;\nDROP TABLE q;"
    statements = split_statements(sql)
    assert len(statements) == 2
    assert "PERFORM 1" in statements[0].text
    assert statements[1].line == 2


def test_parser_ignores_semicolon_in_string_and_comment():
    sql = "INSERT INTO t VALUES ('a;b');\n-- drop; nothing\nDROP TABLE real;"
    statements = split_statements(sql)
    assert len(statements) == 2
    assert statements[1].text == "DROP TABLE real"


def test_drop_table_is_critical():
    findings = check_sql("SET lock_timeout = '3s'; DROP TABLE users;").findings
    assert findings[0].rule == "drop-table"
    assert findings[0].severity == "critical"


def test_unbounded_update_and_delete():
    assert "unbounded-write" in rules_for("SET lock_timeout='1s'; UPDATE users SET a = 1;")
    assert "unbounded-write" in rules_for("SET lock_timeout='1s'; DELETE FROM users;")


def test_batched_backfill_is_only_medium():
    findings = check_sql("SET lock_timeout='1s'; UPDATE users SET a = 1 WHERE id < 100;").findings
    assert [f.severity for f in findings if f.rule == "unbatched-backfill"] == ["medium"]


def test_index_concurrently_required_on_existing_table():
    sql = "SET lock_timeout='1s'; CREATE INDEX idx ON users (email);"
    assert "index-not-concurrent" in rules_for(sql)
    ok = "SET lock_timeout='1s'; CREATE INDEX CONCURRENTLY idx ON users (email);"
    assert "index-not-concurrent" not in rules_for(ok)


def test_index_on_new_table_is_fine():
    sql = "SET lock_timeout='1s'; CREATE TABLE orders (id int); CREATE INDEX idx ON orders (id);"
    assert "index-not-concurrent" not in rules_for(sql)


def test_add_not_null_column_without_default():
    sql = "SET lock_timeout='1s'; ALTER TABLE users ADD COLUMN age int NOT NULL;"
    assert "add-not-null-column" in rules_for(sql)


def test_volatile_default_detected():
    for default in ("now()", "random()", "gen_random_uuid()"):
        sql = f"SET lock_timeout='1s'; ALTER TABLE users ADD COLUMN c timestamptz DEFAULT {default};"
        assert "volatile-default" in rules_for(sql), default


def test_constraint_needs_not_valid():
    bad = "SET lock_timeout='1s'; ALTER TABLE orders ADD CONSTRAINT fk FOREIGN KEY (user_id) REFERENCES users (id);"
    good = "SET lock_timeout='1s'; ALTER TABLE orders ADD CONSTRAINT fk FOREIGN KEY (user_id) REFERENCES users (id) NOT VALID;"
    assert "constraint-without-not-valid" in rules_for(bad)
    assert "constraint-without-not-valid" not in rules_for(good)


def test_alter_type_and_set_not_null():
    assert "alter-column-type" in rules_for("SET lock_timeout='1s'; ALTER TABLE t ALTER COLUMN c TYPE bigint;")
    assert "set-not-null" in rules_for("SET lock_timeout='1s'; ALTER TABLE t ALTER COLUMN c SET NOT NULL;")


def test_missing_timeout_flagged_once():
    findings = check_sql("CREATE TABLE t (id int);").findings
    assert [f.rule for f in findings].count("no-timeout") == 1


def test_clean_migration_has_no_findings():
    sql = """SET lock_timeout = '3s';
SET statement_timeout = '30s';
CREATE TABLE audit (id bigserial primary key, note text);
CREATE INDEX CONCURRENTLY audit_note_idx ON audit (note);
"""
    report = check_sql(sql)
    assert report.findings == []
    assert report.worst == "none"


def test_report_counts_and_ordering():
    sql = "CREATE TABLE t (id int); DROP TABLE old; ALTER TABLE t ALTER COLUMN id TYPE bigint;"
    report = check_sql(sql)
    lines = [f.line for f in report.findings]
    assert lines == sorted(lines)
    assert report.counts()["critical"] == 1
    assert report.worst == "critical"
