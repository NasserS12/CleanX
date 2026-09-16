from pathlib import Path

from core.fs_utils import _is_protected_path


def test_paths():
    result = _is_protected_path(Path("/etc/passwd"))
    assert result is True

def test_another_path():
    result = _is_protected_path(Path("/etcetera/file.txt"))
    assert result is False


def test_home_excat_match_is_protected(monkeypatch):
    monkeypatch.setattr("core.fs_utils.get_user_home", lambda: Path("/esdd/aw/"))
    result = _is_protected_path(Path("/esdd/aw/"))
    assert result is True


def test_home_subfolder_is_not_protected(monkeypatch):
    monkeypatch.setattr("core.fs_utils.get_user_home", lambda: Path("/esdd/aw/"))
    result = _is_protected_path(Path("/esdd/aw/Documentnt"))
    assert result is False



def test_something(tmp_path, monkeypatch):
    critical = tmp_path / "Dan"
    critical.mkdir()

    monkeypatch.setattr("core.fs_utils._PROTECTED_PREFIXES", (str(critical),))

    allowed = tmp_path / "normal"
    allowed.mkdir() 

    link = allowed / "example_link"
    link.symlink_to(critical)   

    result = _is_protected_path(link)
    assert result is True