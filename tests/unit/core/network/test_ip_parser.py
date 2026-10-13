"""
Tests for lanscape.core.ip_parser — IPv4 & IPv6 parsing utilities.
"""

import ipaddress

from lanscape.core.ip_parser import (
    get_address_count,
    ip_range_to_list,
    parse_ip_input,
    parse_ip_networks,
    parse_ip_range,
)


# ---------------------------------------------------------------------------
# IPv4 - existing behavior must be preserved
# ---------------------------------------------------------------------------

class TestParseIpInputIPv4:
    """IPv4 inputs for parse_ip_input."""

    def test_single_ip(self):
        """Single IPv4 address returns one-element list."""
        result = parse_ip_input("192.168.1.1")
        assert result == [ipaddress.IPv4Address("192.168.1.1")]

    def test_cidr_notation(self):
        """CIDR /30 yields 2 usable hosts."""
        result = parse_ip_input("192.168.1.0/30")
        assert len(result) == 2
        assert ipaddress.IPv4Address("192.168.1.1") in result
        assert ipaddress.IPv4Address("192.168.1.2") in result

    def test_full_range(self):
        """Full start-end range is inclusive on both ends."""
        result = parse_ip_input("10.0.0.1-10.0.0.5")
        assert len(result) == 5
        assert result[0] == ipaddress.IPv4Address("10.0.0.1")
        assert result[-1] == ipaddress.IPv4Address("10.0.0.5")

    def test_shorthand_range(self):
        """Shorthand range uses last octet of start IP."""
        result = parse_ip_input("10.0.0.1-5")
        assert len(result) == 5
        assert result[-1] == ipaddress.IPv4Address("10.0.0.5")

    def test_comma_separated(self):
        """Comma-separated single IPs are all collected."""
        result = parse_ip_input("10.0.0.1, 10.0.0.2")
        assert len(result) == 2

    def test_mixed_formats(self):
        """Mix of single, range, and CIDR produces correct total."""
        result = parse_ip_input("10.0.0.1, 10.0.0.10-15, 192.168.1.0/30")
        # 1 + 6 + 2 = 9
        assert len(result) == 9

    def test_large_subnet_no_error(self):
        """Large subnets (e.g. /16) are now parsed without raising."""
        result = parse_ip_input("10.0.0.0/16")
        assert len(result) == 65534


# ---------------------------------------------------------------------------
# IPv6 — new behavior
# ---------------------------------------------------------------------------

class TestParseIpInputIPv6:
    """IPv6 inputs for parse_ip_input."""

    def test_single_ipv6(self):
        """Single IPv6 address returns one-element list."""
        result = parse_ip_input("fd00::1")
        assert result == [ipaddress.IPv6Address("fd00::1")]

    def test_ipv6_cidr(self):
        """IPv6 CIDR /126 yields 3 usable hosts (no broadcast in v6)."""
        result = parse_ip_input("fd00::/126")
        assert len(result) == 3

    def test_ipv6_full_range(self):
        """Full IPv6 start-end range is inclusive."""
        result = parse_ip_input("fd00::1-fd00::5")
        assert len(result) == 5
        assert result[0] == ipaddress.IPv6Address("fd00::1")
        assert result[-1] == ipaddress.IPv6Address("fd00::5")

    def test_ipv6_shorthand_range(self):
        """Shorthand IPv6 range replaces last group."""
        result = parse_ip_input("fd00::1-5")
        assert len(result) == 5
        assert result[0] == ipaddress.IPv6Address("fd00::1")
        assert result[-1] == ipaddress.IPv6Address("fd00::5")

    def test_ipv6_comma_separated(self):
        """Comma-separated IPv6 addresses are all collected."""
        result = parse_ip_input("fd00::1, fd00::2, ::1")
        assert len(result) == 3

    def test_ipv6_mixed_formats(self):
        """Mix of single, range, and CIDR for IPv6."""
        result = parse_ip_input("fd00::1, fd00::10-15, fd00::/126")
        # 1 + 6 + 3 = 10
        assert len(result) == 10

    def test_ipv6_large_subnet_no_error(self):
        """Large IPv6 subnets (e.g. /112) are now parsed without raising."""
        result = parse_ip_input("fd00::/112")
        assert len(result) == 65535

    def test_single_ipv6_128(self):
        """/128 yields exactly 1 host."""
        result = parse_ip_input("::1/128")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Mixed IPv4 + IPv6
# ---------------------------------------------------------------------------

class TestParseIpInputMixed:
    """Comma-separated mixes of IPv4 and IPv6."""

    def test_mixed_v4_and_v6(self):
        """Mixed input contains both address families."""
        result = parse_ip_input("192.168.1.1, fd00::1")
        assert ipaddress.IPv4Address("192.168.1.1") in result
        assert ipaddress.IPv6Address("fd00::1") in result


# ---------------------------------------------------------------------------
# get_address_count
# ---------------------------------------------------------------------------

class TestGetAddressCount:
    """Tests for get_address_count helper."""

    def test_ipv4_subnet(self):
        """IPv4 /24 has 254 scannable hosts (excludes network + broadcast)."""
        assert get_address_count("192.168.1.0/24") == 254

    def test_ipv4_slash31(self):
        """/31 point-to-point link has 2 hosts."""
        assert get_address_count("10.0.0.0/31") == 2

    def test_ipv4_slash32(self):
        """/32 single host."""
        assert get_address_count("10.0.0.1/32") == 1

    def test_ipv6_subnet(self):
        """IPv6 /120 has 255 scannable hosts (excludes network address)."""
        assert get_address_count("fd00::/120") == 255

    def test_ipv6_slash128(self):
        """/128 single host."""
        assert get_address_count("::1/128") == 1

    def test_invalid_returns_zero(self):
        """Invalid input returns 0."""
        assert get_address_count("not-a-subnet") == 0


# ---------------------------------------------------------------------------
# parse_ip_range
# ---------------------------------------------------------------------------

class TestParseIpRange:
    """Tests for parse_ip_range helper."""

    def test_ipv4_full(self):
        """Full IPv4 range returns correct count."""
        result = parse_ip_range("10.0.0.1-10.0.0.3")
        assert len(result) == 3

    def test_ipv4_shorthand(self):
        """Shorthand IPv4 range returns correct count."""
        result = parse_ip_range("10.0.0.1-3")
        assert len(result) == 3

    def test_ipv6_full(self):
        """Full IPv6 range returns IPv6Address objects."""
        result = parse_ip_range("fd00::1-fd00::3")
        assert len(result) == 3
        assert all(isinstance(ip, ipaddress.IPv6Address) for ip in result)

    def test_ipv6_shorthand(self):
        """Shorthand IPv6 range replaces last group correctly."""
        result = parse_ip_range("fd00::1-3")
        assert len(result) == 3
        assert result[-1] == ipaddress.IPv6Address("fd00::3")


# ---------------------------------------------------------------------------
# ip_range_to_list
# ---------------------------------------------------------------------------

class TestIpRangeToList:
    """Tests for ip_range_to_list generator."""

    def test_ipv4(self):
        """IPv4 range yields IPv4Address objects."""
        start = ipaddress.IPv4Address("10.0.0.1")
        end = ipaddress.IPv4Address("10.0.0.3")
        result = list(ip_range_to_list(start, end))
        assert len(result) == 3
        assert all(isinstance(ip, ipaddress.IPv4Address) for ip in result)

    def test_ipv6(self):
        """IPv6 range yields IPv6Address objects."""
        start = ipaddress.IPv6Address("fd00::1")
        end = ipaddress.IPv6Address("fd00::3")
        result = list(ip_range_to_list(start, end))
        assert len(result) == 3
        assert all(isinstance(ip, ipaddress.IPv6Address) for ip in result)

    def test_single_address(self):
        """Range of one address yields single element."""
        ip = ipaddress.IPv4Address("1.2.3.4")
        result = list(ip_range_to_list(ip, ip))
        assert result == [ip]


# ---------------------------------------------------------------------------
# Lists and ranges — networks and address counts without enumerating
# ---------------------------------------------------------------------------

class TestParseIpNetworks:
    """parse_ip_networks covers every target format without enumerating hosts."""

    def test_cidr(self):
        """CIDR entry becomes its network."""
        assert parse_ip_networks("10.0.0.0/24") == [ipaddress.ip_network("10.0.0.0/24")]

    def test_single_addresses_become_host_networks(self):
        """Single IPv4/IPv6 addresses become /32 and /128 networks."""
        assert parse_ip_networks("10.0.0.5, fd00::1") == [
            ipaddress.ip_network("10.0.0.5/32"),
            ipaddress.ip_network("fd00::1/128"),
        ]

    def test_range_is_summarised(self):
        """A range is covered exactly by its summarised networks."""
        nets = parse_ip_networks("10.0.0.1-10.0.0.6")
        covered = [ip for n in nets for ip in n]
        assert covered == parse_ip_input("10.0.0.1-10.0.0.6")

    def test_ipv6_shorthand_range(self):
        """IPv6 shorthand range is summarised."""
        nets = parse_ip_networks("fd00::1-ff")
        assert sum(n.num_addresses for n in nets) == 0xff

    def test_huge_range_does_not_enumerate(self):
        """A /64-sized range returns promptly as a handful of networks."""
        nets = parse_ip_networks("fd00::-fd00::ffff:ffff:ffff:ffff")
        assert nets == [ipaddress.ip_network("fd00::/64")]


class TestGetAddressCountLists:
    """get_address_count handles ranges and comma-separated lists."""

    def test_range(self):
        """Inclusive range count."""
        assert get_address_count("192.168.1.1-192.168.1.10") == 10

    def test_shorthand_range(self):
        """Shorthand range count."""
        assert get_address_count("192.168.1.1-10") == 10

    def test_single_address(self):
        """Single address counts as one."""
        assert get_address_count("fd00::1") == 1

    def test_mixed_list(self):
        """Comma list sums each entry, honouring CIDR host rules."""
        target = "10.0.0.0/30, 10.0.1.5, fd00::1/128, fd00::10-fd00::13"
        assert get_address_count(target) == 2 + 1 + 1 + 4

    def test_invalid_entry_returns_zero(self):
        """Any invalid entry makes the whole target invalid."""
        assert get_address_count("10.0.0.1, not-an-ip") == 0
