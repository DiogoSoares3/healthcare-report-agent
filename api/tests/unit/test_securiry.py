from api.src.tools.stats import validate_sql_safety


def test_sql_safety_guardrail_allows_select():
    """
    Scenario: A standard SELECT query should pass validation (return None).
    """
    valid_query = "SELECT * FROM srag_analytics WHERE age > 60"
    result = validate_sql_safety({"sql_query": valid_query})
    assert result is None


def test_sql_safety_guardrail_blocks_drop():
    """
    Scenario: A DROP command must be intercepted immediately.
    """
    malicious_query = "DROP TABLE srag_analytics"
    result = validate_sql_safety({"sql_query": malicious_query})

    assert result is not None
    assert "Security Violation" in result
    assert "DROP" in result


def test_sql_safety_guardrail_blocks_delete_injection():
    """
    Scenario: Ensures commands hidden in case variations or mixed queries are blocked.
    """
    injection_query = "SELECT * FROM srag_analytics; DELETE FROM srag_analytics;"
    result = validate_sql_safety({"sql_query": injection_query})

    assert result is not None
    assert "Security Violation" in result
    assert "DELETE" in result
