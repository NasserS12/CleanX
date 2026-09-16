import pytest 
from modules.program_removal import _collect_residuals
from pathlib import Path

def test_finds_existing_config_folder(monkeypatch, tmp_path):
    monkeypatch.setattr("modules.program_removal.get_user_home", lambda: tmp_path)

    vlc_config = tmp_path / ".config" / "vlc"
    vlc_config.mkdir(parents=True)

    residuals = _collect_residuals("vlc")

    found_paths = [r["path"] for r in residuals]
    assert vlc_config in found_paths    


def test_alias_finds_folder_with_different_name(monkeypatch, tmp_path):
    monkeypatch.setattr("modules.program_removal.get_user_home", lambda: tmp_path)

    code_folder = tmp_path / ".config" / "Code"
    code_folder.mkdir(parents=True)

    residuals = _collect_residuals("vscode")

    found_paths = [r["path"] for r in residuals]
    assert code_folder in found_paths

def test_empty(monkeypatch,tmp_path):
    monkeypatch.setattr("modules.program_removal.get_user_home", lambda: tmp_path)
    
    residuals = _collect_residuals("Tool")
    assert residuals == []

def test_flatpak(monkeypatch, tmp_path):
    monkeypatch.setattr("modules.program_removal.get_user_home", lambda: tmp_path)
    
    app_folder = tmp_path / ".var" / "app" / "com.spotify.Client"
    app_folder.mkdir(parents=True)

    residuals = _collect_residuals("com.spotify.Client", pm ="flatpak")

    found_paths = [r["path"] for r in residuals]
    assert app_folder in found_paths

def test_glob(monkeypatch,tmp_path):
    monkeypatch.setattr("modules.program_removal.get_user_home", lambda: tmp_path)

    matching_folder = tmp_path / ".config" / "foo-bar"
    matching_folder.mkdir(parents=True)

    another_folder = tmp_path / ".config" / "barstool"
    another_folder.mkdir(parents=True)

    residuals = _collect_residuals("bar")
    found_paths = [r["path"] for r in residuals]

    assert matching_folder in found_paths
    assert another_folder not in found_paths

def test_no_duplicate_when_found_twice(monkeypatch, tmp_path):
    monkeypatch.setattr("modules.program_removal.get_user_home", lambda: tmp_path)

    vlc_folder = tmp_path / ".config" / "vlc"
    vlc_folder.mkdir(parents=True)

    residuals = _collect_residuals("vlc")
    found_paths = [r["path"] for r in residuals]

    assert found_paths.count(vlc_folder) == 1
