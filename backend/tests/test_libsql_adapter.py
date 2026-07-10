from libsql_adapter import LibSQLCursor, _infer_turso_type


def test_infer_turso_type_encodes_booleans_as_string_integers():
    assert _infer_turso_type(True) == ("integer", "1")
    assert _infer_turso_type(False) == ("integer", "0")


def test_cursor_decodes_integer_values_from_turso():
    cursor = LibSQLCursor(
        columns=[{"name": "is_public"}],
        rows=[[{"type": "integer", "value": "0"}]],
    )
    assert cursor.fetchone()["is_public"] == 0
