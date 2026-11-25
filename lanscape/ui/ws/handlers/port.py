"""
WebSocket handler for port list management.

Provides handlers for:
- Listing port lists
- Getting port list details
- Creating, updating, deleting port lists
"""

from typing import Any, Callable, Optional

from lanscape.core.port_manager import PortManager
from lanscape.ui.ws.handlers.base import BaseHandler

_INVALID_NAME_MSG = (
    "Invalid port list name '{name}'. Use 1-64 letters, digits, '_' or '-'."
)
_INVALID_PORTS_MSG = (
    "Invalid port data: expected a non-empty mapping of port numbers "
    "(0-65535) to service name strings."
)


class PortHandler(BaseHandler):
    """
    Handler for port list management WebSocket actions.

    Supports actions:
    - port.list: Get all port list names
    - port.list_summary: Get port lists with port counts
    - port.get: Get a specific port list
    - port.create: Create a new port list
    - port.update: Update an existing port list
    - port.delete: Delete a port list
    """

    def __init__(self, port_manager: Optional[PortManager] = None):
        """
        Initialize the port handler.

        Args:
            port_manager: Optional PortManager instance.
        """
        super().__init__()
        self._port_manager = port_manager or PortManager()

        # Register handlers
        self.register('list', self._handle_list)
        self.register('list_summary', self._handle_list_summary)
        self.register('get', self._handle_get)
        self.register('create', self._handle_create)
        self.register('update', self._handle_update)
        self.register('delete', self._handle_delete)

    @property
    def prefix(self) -> str:
        """Return the action prefix for this handler."""
        return 'port'

    def _handle_list(
        self,
        params: dict[str, Any],  # pylint: disable=unused-argument
        send_event: Optional[Callable] = None  # pylint: disable=unused-argument
    ) -> list:
        """
        Get all available port lists.

        Returns:
            List of port list names
        """
        return self._port_manager.get_port_lists()

    def _handle_list_summary(
        self,
        params: dict[str, Any],  # pylint: disable=unused-argument
        send_event: Optional[Callable] = None  # pylint: disable=unused-argument
    ) -> list:
        """
        Get port list names with their port counts.

        Returns:
            List of dicts with 'name' and 'count' keys, smallest list first
        """
        return [s.model_dump() for s in self._port_manager.get_port_list_summaries()]

    def _handle_get(
        self,
        params: dict[str, Any],
        send_event: Optional[Callable] = None  # pylint: disable=unused-argument
    ) -> dict:
        """
        Get a specific port list by name.

        Params:
            name: Name of the port list to retrieve

        Returns:
            Dict mapping port numbers to service names
        """
        name = self._get_param(params, 'name', required=True)
        port_list = self._port_manager.get_port_list(name)

        if port_list is None:
            raise ValueError(f"Port list not found: {name}")

        return port_list

    def _handle_create(
        self,
        params: dict[str, Any],
        send_event: Optional[Callable] = None  # pylint: disable=unused-argument
    ) -> dict:
        """
        Create a new port list.

        Params:
            name: Name for the new port list
            ports: Dict mapping port numbers to service names

        Returns:
            Dict with success status
        """
        name = self._get_param(params, 'name', required=True)
        ports = self._get_param(params, 'ports', required=True)

        if not PortManager.is_valid_name(name):
            raise ValueError(_INVALID_NAME_MSG.format(name=name))
        if name in self._port_manager.get_port_lists():
            raise ValueError(f"Port list '{name}' already exists.")
        if not self._port_manager.validate_port_data(ports):
            raise ValueError(_INVALID_PORTS_MSG)

        if not self._port_manager.create_port_list(name, ports):
            raise ValueError(f"Failed to create port list '{name}'.")

        return {'success': True, 'name': name}

    def _handle_update(
        self,
        params: dict[str, Any],
        send_event: Optional[Callable] = None  # pylint: disable=unused-argument
    ) -> dict:
        """
        Update an existing port list.

        Params:
            name: Name of the port list to update
            ports: New dict mapping port numbers to service names

        Returns:
            Dict with success status
        """
        name = self._get_param(params, 'name', required=True)
        ports = self._get_param(params, 'ports', required=True)

        if name not in self._port_manager.get_port_lists():
            raise ValueError(f"Port list '{name}' does not exist.")
        if not self._port_manager.validate_port_data(ports):
            raise ValueError(_INVALID_PORTS_MSG)

        if not self._port_manager.update_port_list(name, ports):
            raise ValueError(f"Failed to update port list '{name}'.")

        return {'success': True, 'name': name}

    def _handle_delete(
        self,
        params: dict[str, Any],
        send_event: Optional[Callable] = None  # pylint: disable=unused-argument
    ) -> dict:
        """
        Delete a port list.

        Params:
            name: Name of the port list to delete

        Returns:
            Dict with success status
        """
        name = self._get_param(params, 'name', required=True)

        success = self._port_manager.delete_port_list(name)

        if not success:
            raise ValueError(f"Failed to delete port list '{name}'. It may not exist.")

        return {'success': True, 'name': name}
