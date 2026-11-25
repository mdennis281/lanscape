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


@pytest.mark.parametrize('name', ['../escape', 'a/b', 'a\b', 'x.json', '', ' ', 'a' * 65, None])
def test_create_rejects_unsafe_names(port_dir: Path, name: object) -> None:
    """Names that could escape the ports dir (or are malformed) are refused."""
    pm = PortManager()

    assert not PortManager.is_valid_name(name)  # type: ignore[arg-type]
    assert pm.create_port_list(name, {'22': 'ssh'}) is False  # type: ignore[arg-type]
    assert not (port_dir.parent / 'escape.json').exists()


@pytest.mark.parametrize('name', ['custom', 'My_List-2', 'a' * 64])
def test_create_accepts_safe_names(port_dir: Path, name: str) -> None:
    """Ordinary names create a list on disk."""
    assert PortManager().create_port_list(name, {'22': 'ssh'}) is True
    assert (port_dir / f'{name}.json').exists()


@pytest.mark.usefixtures('port_dir')
@pytest.mark.parametrize('data', [{}, [], None, {'70000': 'x'}, {'22': 1}])
def test_create_rejects_empty_or_invalid_data(data: object) -> None:
    """Empty and malformed port data are refused."""
    assert PortManager().create_port_list('custom', data) is False  # type: ignore[arg-type]


@pytest.mark.usefixtures('port_dir')
def test_summary_counts_track_file_changes() -> None:
    """Counts are cached, but an edited list reports its new size."""
    pm = PortManager()
    assert {s.name: s.count for s in pm.get_port_list_summaries()}['small'] == 2

    pm.update_port_list('small', {'22': 'ssh', '80': 'http', '443': 'https'})

    assert {s.name: s.count for s in pm.get_port_list_summaries()}['small'] == 3


@pytest.mark.usefixtures('port_dir')
def test_summaries_do_not_reparse_unchanged_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    """A second summary call reuses cached counts instead of re-reading files."""
    pm = PortManager()
    pm.get_port_list_summaries()

    def _fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError('port list re-parsed')

    monkeypatch.setattr(pm, 'get_port_list', _fail)
    assert [s.name for s in pm.get_port_list_summaries()][-1] == 'full'
