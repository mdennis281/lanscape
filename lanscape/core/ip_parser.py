"""IP address parsing utilities (single, CIDR, ranges) — IPv4 & IPv6."""
import ipaddress
from typing import List, Tuple, Union

IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def _is_ipv6(text: str) -> bool:
    """Return True when *text* looks like an IPv6 address or prefix."""
    return ':' in text.split('/')[0]


def parse_ip_input(ip_input: str) -> List[IPAddress]:
    """
    Parse various IP address format inputs into a list of IP address objects.

    Supports (both IPv4 **and** IPv6):
    - Comma-separated entries
    - CIDR notation (e.g., 192.168.1.0/24 or fd00::/120)
    - IP ranges with a hyphen (e.g., 192.168.1.1-192.168.1.10 or fd00::1-fd00::ff)
    - Shorthand IPv4 ranges (e.g., 192.168.1.1-10)
    - Single IP addresses

    Args:
        ip_input (str): String containing IP addresses in various formats

    Returns:
        list: List of IPv4Address / IPv6Address objects
    """
    entries = [entry.strip() for entry in ip_input.split(',')]
    ip_ranges: List[IPAddress] = []

    for entry in entries:
        # Handle CIDR notation
        if '/' in entry:
            net = ipaddress.ip_network(entry, strict=False)
            if isinstance(net, ipaddress.IPv6Network):
                # IPv6 has no broadcast address — include all except network address
                if net.num_addresses == 1:          # /128 — single host
                    ip_ranges.append(net.network_address)
                else:
                    for ip_int in range(1, net.num_addresses):
                        ip_ranges.append(net.network_address + ip_int)
            else:
                for ip in net.hosts():
                    ip_ranges.append(ip)

        # Handle IP range (e.g., 10.0.0.15-10.0.0.25 or fd00::1-fd00::ff)
        elif '-' in entry:
            ip_ranges += parse_ip_range(entry)

        # Single IP address
        else:
            ip_ranges.append(ipaddress.ip_address(entry))

    return ip_ranges


def parse_ip_networks(ip_input: str) -> List[IPNetwork]:
    """
    Parse a target string into the networks it covers, without enumerating hosts.

    Accepts every format :func:`parse_ip_input` does. CIDR entries become their
    network, ranges are summarised into the minimal covering networks, and single
    addresses become a host network (/32 or /128).

    Args:
        ip_input (str): String containing IP addresses in various formats

    Returns:
        list: IPv4Network / IPv6Network objects, one or more per entry

    Raises:
        ValueError: If any entry cannot be parsed
    """
    networks: List[IPNetwork] = []
    for entry in (e.strip() for e in ip_input.split(',')):
        if '/' in entry:
            networks.append(ipaddress.ip_network(entry, strict=False))
        elif '-' in entry:
            start, end = _parse_range_bounds(entry)
            networks.extend(ipaddress.summarize_address_range(start, end))
        else:
            networks.append(ipaddress.ip_network(entry))
    return networks


def get_address_count(subnet: str) -> int:
    """
    Get the number of scannable host addresses in a target (IPv4 or IPv6).

    Accepts CIDR, ranges, single addresses and comma-separated lists of them.
    For an IPv4 CIDR this excludes the network and broadcast addresses (except
    for /31 and /32); for an IPv6 CIDR it excludes only the network address.
    Ranges and single addresses count every address they name.

    Args:
        subnet (str): Target string

    Returns:
        int: Number of scannable host addresses, or 0 if invalid
    """
    try:
        total = 0
        for entry in (e.strip() for e in subnet.split(',')):
            if '/' in entry:
                total += _cidr_host_count(ipaddress.ip_network(entry, strict=False))
            elif '-' in entry:
                start, end = _parse_range_bounds(entry)
                total += max(int(end) - int(start) + 1, 0)
            else:
                ipaddress.ip_address(entry)
                total += 1
        return total
    except (ValueError, TypeError):
        return 0


def _cidr_host_count(net: IPNetwork) -> int:
    """Return the scannable host count of a single CIDR network."""
    if isinstance(net, ipaddress.IPv6Network):
        # IPv6: exclude network address only (no broadcast)
        return max(net.num_addresses - 1, 1)
    # IPv4: /32 = 1 host, /31 = 2 hosts, else num_addresses - 2
    if net.prefixlen >= 31:
        return net.num_addresses
    return net.num_addresses - 2


def parse_ip_range(entry: str) -> List[IPAddress]:
    """
    Parse an IP range specified with a hyphen.

    IPv4 examples:
    - ``192.168.1.1-192.168.1.10``
    - ``192.168.1.1-10``  (shorthand — last octet only)

    IPv6 examples:
    - ``fd00::1-fd00::ff``
    - ``fd00::1-ff``  (shorthand — last group only)

    Args:
        entry (str): String containing an IP range with a hyphen

    Returns:
        list: List of IPv4Address / IPv6Address objects in the range (inclusive)
    """
    start_ip, end_ip = _parse_range_bounds(entry)
    return list(ip_range_to_list(start_ip, end_ip))


def _parse_range_bounds(entry: str) -> Tuple[IPAddress, IPAddress]:
    """Return the (start, end) addresses of a hyphenated range entry."""
    if _is_ipv6(entry):
        return _ipv6_range_bounds(entry)
    return _ipv4_range_bounds(entry)


def _ipv4_range_bounds(entry: str) -> Tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]:
    """Bounds of an IPv4 range like ``192.168.1.1-10`` or ``192.168.1.1-192.168.1.10``."""
    start_str, end_str = entry.split('-')
    start_ip = ipaddress.IPv4Address(start_str.strip())

    # Shorthand: second part is just the last octet
    if '.' not in end_str:
        end_str = start_ip.exploded.rsplit('.', 1)[0] + '.' + end_str.strip()

    return start_ip, ipaddress.IPv4Address(end_str.strip())


def _ipv6_range_bounds(entry: str) -> Tuple[ipaddress.IPv6Address, ipaddress.IPv6Address]:
    """Bounds of an IPv6 range like ``fd00::1-fd00::ff`` or ``fd00::1-ff``."""
    # Split on the last hyphen so addresses with ``::`` remain intact.
    idx = entry.rfind('-')
    start_str = entry[:idx].strip()
    end_str = entry[idx + 1:].strip()

    start_ip = ipaddress.IPv6Address(start_str)

    # Shorthand: end part contains no colons → replace last group of start
    if ':' not in end_str:
        prefix = start_ip.exploded.rsplit(':', 1)[0]
        end_str = f"{prefix}:{int(end_str, 16):04x}"

    return start_ip, ipaddress.IPv6Address(end_str)


def ip_range_to_list(
    start_ip: IPAddress,
    end_ip: IPAddress,
):
    """
    Convert an IP range defined by start and end addresses to a list of addresses.

    Args:
        start_ip: The starting IP address (IPv4Address or IPv6Address)
        end_ip: The ending IP address (IPv4Address or IPv6Address)

    Yields:
        IPv4Address | IPv6Address: Each IP address in the range (inclusive)
    """
    addr_cls = type(start_ip)
    for ip_int in range(int(start_ip), int(end_ip) + 1):
        yield addr_cls(ip_int)
