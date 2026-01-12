from api.src.tools.stats import validate_sql_safety


def test_sql_safety_guardrail_allows_select():
    """
    Verifies that benign SQL queries are permitted.

    **Scenario:**
    User asks for a simple data extraction (SELECT).

    **Expectation:**
    The validator returns `None` (indicating no error/violation).
    """
    valid_query = "SELECT * FROM srag_analytics WHERE age > 60"
    result = validate_sql_safety({"sql_query": valid_query})
    assert result is None


def test_sql_safety_guardrail_blocks_drop():
    """
    Verifies that destructive `DROP` commands are blocked.

    **Scenario:**
    User (or hallucinating LLM) attempts to delete the main table.

    **Expectation:**
    The validator returns a string containing "Security Violation".
    """
    malicious_query = "DROP TABLE srag_analytics"
    result = validate_sql_safety({"sql_query": malicious_query})

    assert result is not None
    assert "Security Violation" in result
    assert "DROP" in result


def test_sql_safety_guardrail_blocks_delete_injection():
    """
    Verifies detection of SQL Injection attempts using chained commands.

    **Scenario:**
    The input starts with a valid SELECT but appends a malicious DELETE command
    after a semicolon (`;`).

    **Expectation:**
    The validator detects the hidden `DELETE` keyword and blocks the execution.
    """
    injection_query = "SELECT * FROM srag_analytics; DELETE FROM srag_analytics;"
    result = validate_sql_safety({"sql_query": injection_query})

    assert result is not None
    assert "Security Violation" in result
    assert "DELETE" in result
