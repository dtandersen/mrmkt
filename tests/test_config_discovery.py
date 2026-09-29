"""Tests for .mrmkt/ config discovery with legacy cwd fallback."""

from pathlib import Path

import pytest
from hamcrest import assert_that, equal_to, none, not_none

from mrmkt.command._shared import load_local_config
from mrmkt.common.config import find_config_file, read_config


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_finds_dotmrmkt_config_in_start_dir(tmp_path):
    _write(tmp_path / ".mrmkt" / "config.yaml", "rabbitmq: {}\n")

    found = find_config_file("config.yaml", tmp_path)

    assert_that(found, equal_to(tmp_path / ".mrmkt" / "config.yaml"))


def test_walks_up_to_parent_dotmrmkt(tmp_path):
    _write(tmp_path / ".mrmkt" / "alpaca.yaml", "key: x\n")
    nested = tmp_path / "stocks" / "notes"
    nested.mkdir(parents=True)

    found = find_config_file("alpaca.yaml", nested)

    assert_that(found, equal_to(tmp_path / ".mrmkt" / "alpaca.yaml"))


def test_closer_dotmrmkt_wins_over_farther(tmp_path):
    _write(tmp_path / ".mrmkt" / "dbschema.yml", "outer: true\n")
    inner = tmp_path / "inner"
    _write(inner / ".mrmkt" / "dbschema.yml", "inner: true\n")

    found = find_config_file("dbschema.yml", inner)

    assert_that(found, equal_to(inner / ".mrmkt" / "dbschema.yml"))


def test_legacy_bare_file_used_when_no_dotmrmkt_anywhere(tmp_path):
    _write(tmp_path / "config.yaml", "legacy: true\n")

    found = find_config_file("config.yaml", tmp_path)

    assert_that(found, equal_to(tmp_path / "config.yaml"))


def test_dotmrmkt_beats_legacy_bare_file(tmp_path):
    _write(tmp_path / "config.yaml", "legacy: true\n")
    _write(tmp_path / ".mrmkt" / "config.yaml", "managed: true\n")

    found = find_config_file("config.yaml", tmp_path)

    assert_that(found, equal_to(tmp_path / ".mrmkt" / "config.yaml"))


def test_returns_none_when_nothing_exists(tmp_path):
    assert_that(find_config_file("config.yaml", tmp_path), none())


def test_read_config_reads_dotmrmkt_copy(tmp_path):
    _write(tmp_path / ".mrmkt" / "config.yaml", "rabbitmq:\n  host: example\n")

    config = read_config(tmp_path)

    assert_that(config, equal_to({"rabbitmq": {"host": "example"}}))


def test_read_config_missing_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_config(tmp_path)


def test_load_local_config_reads_dotmrmkt_and_defaults_empty(tmp_path):
    assert_that(load_local_config(tmp_path), equal_to({}))

    _write(tmp_path / ".mrmkt" / "config.yaml", "a: 1\n")

    assert_that(load_local_config(tmp_path), equal_to({"a": 1}))


def test_load_local_config_invalid_yaml_means_empty(tmp_path):
    _write(tmp_path / ".mrmkt" / "config.yaml", ": : : not yaml : :\n{")

    assert_that(load_local_config(tmp_path), equal_to({}))


def test_found_path_is_usable_for_required_configs(tmp_path):
    _write(tmp_path / ".mrmkt" / "alpaca.yaml", "endpoint: x\nkey: y\nsecret: z\n")

    found = find_config_file("alpaca.yaml", tmp_path)

    assert_that(found, not_none())
    assert_that("endpoint" in (found.read_text() if found else ""), equal_to(True))
