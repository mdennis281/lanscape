"""Tests for PortManager listing, ordering and side effects."""

import json
from pathlib import Path

import pytest

from lanscape.core.port_manager import PortManager, PortListSummary


@pytest.fixture
def port_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point PortManager at an isolated ports directory with unordered lists."""
    ports = tmp_path / 'ports'
    ports.mkdir()
    lists = {
        'medium': {str(p): 'svc' for p in range(1, 6)},
        'full': {str(p): 'svc' for p in range(1, 11)},
        'small': {'22': 'ssh', '80': 'http'},
        'alpha': {'1': 'a', '2': 'b'},
        'broken': {'not-a-port': 'svc'},
    }
    for name, data in lists.items():
        (ports / f'{name}.json').write_text(json.dumps(data), encoding='utf-8')
    (ports / 'convert_csv.py').write_text('', encoding='utf-8')

    monkeypatch.setattr(
        'lanscape.core.app_scope.ResourceManager._get_resource_path',
        lambda self: tmp_path,
    )
    return ports


@pytest.mark.usefixtures('port_dir')
def test_get_port_lists_is_sorted_and_json_only() -> None:
    """Names come back alphabetically, ignoring non-JSON files."""
    assert PortManager().get_port_lists() == ['alpha', 'broken', 'full', 'medium', 'small']


@pytest.mark.usefixtures('port_dir')
def test_summaries_ordered_smallest_first() -> None:
    """Summaries are ordered by port count, with name breaking ties."""
    summaries = PortManager().get_port_list_summaries()

    assert [s.name for s in summaries] == ['broken', 'alpha', 'small', 'medium', 'full']
    assert all(isinstance(s, PortListSummary) for s in summaries)
    assert {s.name: s.count for s in summaries}['broken'] == 0
    counts = [s.count for s in summaries]
    assert counts == sorted(counts)


def test_init_does_not_create_dir_in_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Constructing a PortManager must not litter the working directory."""
    cwd = tmp_path / 'cwd'
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    PortManager()

    assert not any(cwd.iterdir())


def test_shipped_lists_exclude_test_fixtures() -> None:
    """Only user-facing port lists ship in the package resources."""
    names = PortManager().get_port_lists()

    assert not [n for n in names if n.startswith('test')]
    assert {'small', 'medium', 'large', 'full'} <= set(names)


def test_shipped_summaries_grow_in_size() -> None:
    """The built-in lists appear smallest to largest."""
    order = [s.name for s in PortManager().get_port_list_summaries()]

    builtins = [n for n in order if n in {'small', 'medium', 'large', 'full'}]
    assert builtins == ['small', 'medium', 'large', 'full']
