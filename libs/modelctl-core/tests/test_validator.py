"""Tests for file validation."""

import hashlib
import tempfile
from pathlib import Path

from modelctl_core import validator


def test_sha256():
    data = b"hello world"
    f = Path(tempfile.mktemp())
    f.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert validator.sha256(f) == expected
    f.unlink()


def test_validate_file_not_found():
    issues = validator.validate_file(Path("/nonexistent/file.gguf"))
    assert len(issues) == 1
    assert "not found" in issues[0]


def test_validate_file_empty(tmp_path):
    f = tmp_path / "empty.gguf"
    f.write_text("")
    issues = validator.validate_file(f)
    assert any("empty" in i for i in issues)


def test_validate_file_size_mismatch(tmp_path):
    f = tmp_path / "model.gguf"
    f.write_bytes(b"x" * 100)
    issues = validator.validate_file(f, expected_size=200)
    assert any("mismatch" in i for i in issues)


def test_validate_file_size_match(tmp_path):
    f = tmp_path / "model.gguf"
    f.write_bytes(b"x" * 100)
    issues = validator.validate_file(f, expected_size=100)
    assert all("mismatch" not in i for i in issues)


def test_validate_gguf_magic_bytes(tmp_path):
    # Valid GGUF magic: GGUF = 0x47 0x47 0x55 0x46
    f = tmp_path / "model.gguf"
    f.write_bytes(b"\x47\x47\x55\x46" + b"\x00" * 100)
    issues = validator.validate_file(f)
    gguf_issues = [i for i in issues if "magic" in i.lower()]
    assert len(gguf_issues) == 0


def test_validate_invalid_gguf_magic(tmp_path):
    f = tmp_path / "model.gguf"
    f.write_bytes(b"\x00\x01\x02\x03" + b"\x00" * 100)
    issues = validator.validate_file(f)
    gguf_issues = [i for i in issues if "magic" in i.lower()]
    assert len(gguf_issues) == 1


def test_validate_non_gguf_skips_magic_check(tmp_path):
    f = tmp_path / "config.json"
    f.write_bytes(b"{}\n")
    issues = validator.validate_file(f)
    magic_issues = [i for i in issues if "magic" in i.lower()]
    assert len(magic_issues) == 0


def test_no_issues_for_valid_file(tmp_path):
    f = tmp_path / "model.gguf"
    f.write_bytes(b"\x47\x47\x55\x46" + b"\x00" * 1000)
    issues = validator.validate_file(f, expected_size=1004)
    assert len(issues) == 0
