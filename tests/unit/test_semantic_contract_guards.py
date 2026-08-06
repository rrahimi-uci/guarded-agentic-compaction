from guarded_agentic_compaction.grc.contracts import (
    MAX_ENUM_CARDINALITY,
    _field_clauses,
    _opaque_identifier_path,
)


def test_opaque_identifier_paths_are_not_treated_as_continuous_features() -> None:
    for path in ("issue_number", "record_number", "ticket_id", "tenant.key"):
        assert _opaque_identifier_path(path)
    assert not _opaque_identifier_path("priority")
    assert not _opaque_identifier_path("amount")


def test_high_cardinality_text_gets_type_not_empirical_regex_hull() -> None:
    results = [
        {"title": f"Distinct public issue title {index}"}
        for index in range(MAX_ENUM_CARDINALITY + 1)
    ]
    [(path, hull, type_name, min_len, max_len)] = _field_clauses(results, limit=4)
    assert path == "title"
    assert type_name == "str"
    assert hull.kind == "any"
    assert min_len is None
    assert max_len is None


def test_identifier_output_gets_no_empirical_numeric_interval() -> None:
    results = [{"record_number": value} for value in (10, 20, 30)]
    [(path, hull, type_name, min_len, max_len)] = _field_clauses(results, limit=4)
    assert (path, type_name, hull.kind, min_len, max_len) == (
        "record_number", "int", "any", None, None
    )
