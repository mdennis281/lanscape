"""Port list CRUD operations (stored as JSON files)."""

import json
from typing import List

from pydantic import BaseModel, Field

from .app_scope import ResourceManager

PORT_DIR = 'ports'


class PortListSummary(BaseModel):
    """A port list's name and how many ports it contains."""
    name: str = Field(description="Port list name (without the .json extension)")
    count: int = Field(description="Number of ports in the list")


class PortManager:
    """CRUD manager for port list JSON files."""

    def __init__(self):
        """Initialize the PortManager over the packaged ports resource directory."""
        self.rm = ResourceManager(PORT_DIR)

    def get_port_lists(self) -> List[str]:
        """
        Get a list of all available port list names, sorted alphabetically.

        Returns:
            List[str]: Names of all available port lists (without .json extension)
        """
        return sorted(f.removesuffix('.json') for f in self.rm.list() if f.endswith('.json'))

    def get_port_list_summaries(self) -> List[PortListSummary]:
        """
        Get every port list with its port count, smallest list first.

        Lists with the same count are ordered by name. A list whose data
        fails validation is reported with a count of 0.

        Returns:
            List[PortListSummary]: One summary per port list, ordered by size
        """
        summaries = [
            PortListSummary(name=name, count=len(self.get_port_list(name) or {}))
            for name in self.get_port_lists()
        ]
        return sorted(summaries, key=lambda s: (s.count, s.name))

    def get_port_list(self, port_list: str) -> dict | None:
        """
        Retrieve a port list by name.

        Args:
            port_list (str): The name of the port list to retrieve

        Returns:
            dict | None: A dictionary of port numbers to service names,
            or None if the stored data fails validation

        Raises:
            ValueError: If the specified port list does not exist
        """
        if port_list not in self.get_port_lists():
            msg = f"Port list '{port_list}' does not exist. "
            msg += f"Available port lists: {self.get_port_lists()}"
            raise ValueError(msg)

        data = json.loads(self.rm.get(f'{port_list}.json'))

        return data if self.validate_port_data(data) else None

    def create_port_list(self, port_list: str, data: dict) -> bool:
        """
        Create a new port list.

        Args:
            port_list (str): Name for the new port list
            data (dict): Dictionary mapping port numbers to service names

        Returns:
            bool: True if creation was successful, False otherwise
        """
        if port_list in self.get_port_lists():
            return False
        if not self.validate_port_data(data):
            return False

        self.rm.create(f'{port_list}.json', json.dumps(data, indent=2))

        return True

    def update_port_list(self, port_list: str, data: dict) -> bool:
        """
        Update an existing port list.

        Args:
            port_list (str): Name of the port list to update
            data (dict): New dictionary mapping port numbers to service names

        Returns:
            bool: True if update was successful, False otherwise
        """
        if port_list not in self.get_port_lists():
            return False
        if not self.validate_port_data(data):
            return False

        self.rm.update(f'{port_list}.json', json.dumps(data, indent=2))

        return True

    def delete_port_list(self, port_list: str) -> bool:
        """
        Delete a port list.

        Args:
            port_list (str): Name of the port list to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if port_list not in self.get_port_lists():
            return False

        self.rm.delete(f'{port_list}.json')

        return True

    def validate_port_data(self, port_data: dict) -> bool:
        """
        Validate port data structure and content.

        Ensures that:
        - Keys can be converted to integers
        - Values are strings
        - Port numbers are within valid range (0-65535)

        Args:
            port_data (dict): Dictionary mapping port numbers to service names

        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            for port, service in port_data.items():
                port = int(port)  # throws if not int
                if not isinstance(service, str):
                    return False

                if not 0 <= port <= 65535:
                    return False
            return True
        except (ValueError, TypeError, AttributeError):
            return False
