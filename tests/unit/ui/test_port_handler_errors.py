"""PortHandler create/update errors name the actual problem."""

import json
from pathlib import Path

import pytest

from lanscape.core.port_manager import PortManager
from lanscape.ui.ws.handlers.port import PortHandler


@pytest.fixture
def handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PortHandler:
    """A PortHandler backed by a real PortManager over a temp ports dir."""
    ports = tmp_path / 'ports'
    ports.mkdir()
    (ports / 'small.json').write_text(json.dumps({'22': 'ssh'}), encoding='utf-8')
    monkeypatch.setattr(
        'lanscape.core.app_scope.ResourceManager._get_resource_path',
        lambda self: tmp_path,
    )
    return PortHandler(port_manager=PortManager())


@pytest.mark.parametrize(('params', 'match'), [
    ({'name': '../x', 'ports': {'22': 'ssh'}}, 'Invalid port list name'),
    ({'name': 'small', 'ports': {'22': 'ssh'}}, 'already exists'),
    ({'name': 'custom', 'ports': {}}, 'Invalid port data'),
    ({'name': 'custom', 'ports': {'99999': 'x'}}, 'Invalid port data'),
])
def test_create_errors(handler: PortHandler, params: dict, match: str) -> None:
    """Each create failure reports its specific cause."""
    with pytest.raises(ValueError, match=match):
        handler.invoke('create', params)


@pytest.mark.parametrize(('params', 'match'), [
    ({'name': 'missing', 'ports': {'22': 'ssh'}}, 'does not exist'),
    ({'name': 'small', 'ports': {}}, 'Invalid port data'),
])
def test_update_errors(handler: PortHandler, params: dict, match: str) -> None:
    """Each update failure reports its specific cause."""
    with pytest.raises(ValueError, match=match):
        handler.invoke('update', params)


def test_create_then_listed(handler: PortHandler) -> None:
    """A successful create shows up in the size-ordered summary."""
    assert handler.invoke('create', {'name': 'custom', 'ports': {'22': 'a', '80': 'b'}})['success']

    assert handler.invoke('list_summary') == [
        {'name': 'small', 'count': 1},
        {'name': 'custom', 'count': 2},
    ]
