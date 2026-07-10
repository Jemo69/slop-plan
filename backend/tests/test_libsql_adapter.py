from libsql_adapter import _infer_turso_type


def test_infer_turso_type_encodes_booleans_as_string_integers():
    assert _infer_turso_type(True) == ("integer", "1")
    assert _infer_turso_type(False) == ("integer", "0")
