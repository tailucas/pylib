def test_import_non_optional():
    pass

def test_import_basics():
    from tailucas_pylib import APP_NAME, log, threads

    assert threads is not None
    assert APP_NAME is not None
    assert log is not None
