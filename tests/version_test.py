from pollination_dsl.common import _clean_version


def test_dev_version():
    v = '0.1.dev1+gf910655.d20210207'
    version = _clean_version(v)
    assert version == '0.1.0'


def test_dev_version_2():
    v = '0.1.2.dev1+gf910655.d20210207'
    version = _clean_version(v)
    assert version == '0.1.2'


def test_version():
    v = '0.1.2'
    version = _clean_version(v)
    assert version == '0.1.2'
