def test_import_non_optional():
    import dateutil.parser
    import yaml
    import pytz
    pass

def test_import_basics():
    from tailucas_pylib import threads
    from tailucas_pylib import APP_NAME, log

    assert threads is not None
    assert APP_NAME is not None
    assert log is not None
