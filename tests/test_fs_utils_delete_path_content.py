from core import state
from core.fs_utils import delete_path_content


def test_delete_regular_file(monkeypatch, tmp_path):
    monkeypatch.setattr("core.fs_utils.check_sudo_status", lambda: False)

    my_file = tmp_path / "file.txt"
    my_file.write_text("some data")

    result = delete_path_content(my_file)

    assert result is True
    assert my_file.exists() is False

def test_delete_symlink(monkeypatch , tmp_path):
    monkeypatch.setattr("core.fs_utils.check_sudo_status", lambda: False)
    
    my_file = tmp_path / "test.txt"
    my_file.write_text("some data")

    sym_file = tmp_path / "sym.txt"
    sym_file.symlink_to(my_file)

    result = delete_path_content(sym_file)
    assert result is True
    assert my_file.exists() is True
    assert sym_file.is_symlink() is False

def test_link_broken(monkeypatch,tmp_path):
    monkeypatch.setattr("core.fs_utils.check_sudo_status", lambda: False)

    missing_target = tmp_path / "does_not_exist.txt"

    sym_file = tmp_path / "sym_broken"
    sym_file.symlink_to(missing_target)

    assert sym_file.exists() is False
    assert sym_file.is_symlink() is True

    result = delete_path_content(sym_file)
    assert result is True
    assert sym_file.is_symlink() is False

def test_protect_path(monkeypatch, tmp_path):
    critical = tmp_path / "stc"
    critical.mkdir()

    monkeypatch.setattr("core.fs_utils._PROTECTED_PREFIXES", (str(critical),))

    protected_file = critical / "important.txt"
    protected_file.write_text("do not delete")

    result = delete_path_content(protected_file)

    assert result is False
    assert protected_file.exists() is True

def test_Dry_run(monkeypatch,tmp_path):    
    state.IS_DRY_RUN = True

    my_file = tmp_path / "file.txt"
    my_file.write_text("Some data")

    result = delete_path_content(my_file)
    
    assert result is True
    assert my_file.exists() is True

    state.IS_DRY_RUN = False