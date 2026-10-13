"""
Tests for subnet classification helpers used by stage guards.

``is_ipv6_subnet``, ``is_local_subnet`` and ``matching_interface`` must accept
every target format the scanner does — CIDR, ranges, single addresses and
comma-separated lists — not just a single CIDR.
"""

from unittest.mock import patch

import pytest

from lanscape.core.net_tools.subnet_utils import (
    is_ipv6_subnet,
    is_local_subnet,
    matching_interface,
)


_INTERFACES = [
    {'subnet': '192.168.1.0/24', 'address_cnt': 254, 'interface': 'eth0'},
    {'subnet': 'fd00:dead:beef::/64', 'address_cnt': 100_000, 'interface': 'eth1'},
]


@pytest.fixture
def local_interfaces():
    """Pretend this machine has one IPv4 and one IPv6 interface."""
    with patch(
        'lanscape.core.net_tools.subnet_utils.get_all_network_subnets',
        return_value=_INTERFACES,
    ):
        yield


class TestIsIPv6Subnet:
    """is_ipv6_subnet classifies every target format."""

    @pytest.mark.parametrize("target", [
        "fd00::/64",
        "fd00::1",
        "fd00::1-fd00::ff",
        "fd00::10/128, fd00::11/128",
        "fd00::1, fd00::2-ff",
    ])
    def test_ipv6_targets(self, target):
        """Pure IPv6 targets are IPv6."""
        assert is_ipv6_subnet(target) is True

    @pytest.mark.parametrize("target", [
        "192.168.1.0/24",
        "10.0.0.1-10.0.0.50",
        "10.0.0.1, 10.0.0.2",
    ])
    def test_ipv4_targets(self, target):
        """Pure IPv4 targets are not IPv6."""
        assert is_ipv6_subnet(target) is False

    def test_mixed_list_is_not_ipv6_only(self):
        """A mixed list is not IPv6-only, so IPv4-gated stages still run for it."""
        assert is_ipv6_subnet("1.1.1.1, fd00::1") is False


@pytest.mark.usefixtures("local_interfaces")
class TestIsLocalSubnet:
    """is_local_subnet / matching_interface handle lists and ranges."""

    @pytest.mark.parametrize("target,iface", [
        ("192.168.1.0/24", "eth0"),
        ("192.168.1.10-192.168.1.20", "eth0"),
        ("192.168.1.5, 192.168.1.6", "eth0"),
        ("fd00:dead:beef::10/128, fd00:dead:beef::11/128", "eth1"),
        ("fd00:dead:beef::1-ff", "eth1"),
        ("8.8.8.8, 192.168.1.5", "eth0"),
    ])
    def test_local_targets(self, target, iface):
        """Targets overlapping a local interface are local."""
        assert is_local_subnet(target) is True
        assert matching_interface(target) == iface

    @pytest.mark.parametrize("target", [
        "10.99.0.0/16",
        "10.99.0.1-10.99.0.9",
        "2001:db8::1, 8.8.8.8",
    ])
    def test_remote_targets(self, target):
        """Targets with no overlap are remote."""
        assert is_local_subnet(target) is False
        assert matching_interface(target) is None

    def test_invalid_target_is_not_local(self):
        """Unparseable input is never local."""
        assert is_local_subnet("not-a-subnet") is False
