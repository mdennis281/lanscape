# PortManager

`lanscape.PortManager`

CRUD manager for port list configurations. Port lists are stored as JSON files in the packaged `lanscape/resources/ports/` directory, mapping port numbers to service names. The scanner uses these lists to determine which ports to test on each device.

## Import

```python
from lanscape import PortManager, PortListSummary
```

## Constructor

```python
pm = PortManager()
```

Initializes an internal `ResourceManager` over the packaged `lanscape/resources/ports/` directory. Nothing is created on disk — in particular, no `ports/` directory is made in the current working directory. Lists created, updated or deleted through this class are written to that packaged directory, so they live inside the installed `lanscape` package.

## Built-in Port Lists

LANscape ships with four built-in port lists:

| Name | Ports | Description |
|------|-------|-------------|
| `small` | 20 | Common ports (HTTP, SSH, DNS, etc.) |
| `medium` | 148 | Well-known ports |
| `large` | 6085 | Broad coverage for thorough scanning |
| `full` | 65535 | Every port from 1 to 65535 |

## Methods

### `get_port_lists() -> List[str]`

List all available port list names, sorted alphabetically.

**Returns:** `List[str]` — names without the `.json` extension.

```python
pm = PortManager()
print(pm.get_port_lists())
# ['full', 'large', 'medium', 'small']
```

To order lists by size instead, use [`get_port_list_summaries()`](#get_port_list_summaries---listportlistsummary).

---

### `get_port_list_summaries() -> List[PortListSummary]`

List every port list with its port count, smallest list first. Lists with the same count are ordered by name. A list whose stored data fails [validation](#validate_port_dataport_data-dict---bool) is reported with a count of `0`.

**Returns:** `List[PortListSummary]` — one [`PortListSummary`](#portlistsummary) per port list, ordered by size.

```python
pm = PortManager()
for summary in pm.get_port_list_summaries():
    print(summary.name, summary.count)
# small 20
# medium 148
# large 6085
# full 65535
```

This is the ordering the WebSocket [`port.list_summary`](websocket-server.md#portlist_summary) action returns.

Counts are cached per `PortManager` instance, keyed on each file's modification time and size, so repeated calls do not re-parse large lists such as `full`. A list that is edited on disk is re-counted on the next call.

---

### `get_port_list(port_list: str) -> dict | None`

Retrieve a port list by name.

| Parameter | Type | Description |
|-----------|------|-------------|
| `port_list` | `str` | Name of the port list |

**Returns:** `dict | None` — mapping of port number (as string key) to service name, or `None` if the stored data fails [validation](#validate_port_dataport_data-dict---bool).

**Raises:** `ValueError` if the port list does not exist.

```python
ports = pm.get_port_list("small")
# {"22": "SSH", "80": "HTTP", "443": "HTTPS", ...}
```

---

### `is_valid_name(port_list: str) -> bool`

*Static method.* Check whether a string is an acceptable port list name. Names become file names, so they are limited to **1–64 characters** drawn from letters, digits, `_` and `-` — no spaces, dots or path separators.

| Parameter | Type | Description |
|-----------|------|-------------|
| `port_list` | `str` | Candidate port list name |

**Returns:** `bool` — `True` if the name is valid. Non-string input returns `False`.

```python
PortManager.is_valid_name("web-servers")  # True
PortManager.is_valid_name("my_list_2")    # True
PortManager.is_valid_name("my list")      # False (space)
PortManager.is_valid_name("../x")         # False (dots and slash)
PortManager.is_valid_name("")             # False (empty)
```

---

### `create_port_list(port_list: str, data: dict) -> bool`

Create a new port list.

| Parameter | Type | Description |
|-----------|------|-------------|
| `port_list` | `str` | Name for the new port list (see [`is_valid_name()`](#is_valid_nameport_list-str---bool)) |
| `data` | `dict` | Mapping of port numbers to service names |

**Returns:** `bool` — `True` if created successfully, `False` if the name is invalid, a list with that name already exists, or the data is [invalid](#validate_port_dataport_data-dict---bool).

```python
custom_ports = {
    "8080": "HTTP-Alt",
    "8443": "HTTPS-Alt",
    "9090": "Prometheus"
}
pm.create_port_list("my-custom", custom_ports)
```

---

### `update_port_list(port_list: str, data: dict) -> bool`

Update an existing port list.

| Parameter | Type | Description |
|-----------|------|-------------|
| `port_list` | `str` | Name of the port list to update |
| `data` | `dict` | New mapping of port numbers to service names |

**Returns:** `bool` — `True` if updated, `False` if the list doesn't exist or data is invalid.

---

### `delete_port_list(port_list: str) -> bool`

Delete a port list.

| Parameter | Type | Description |
|-----------|------|-------------|
| `port_list` | `str` | Name of the port list to delete |

**Returns:** `bool` — `True` if deleted, `False` if the list doesn't exist.

---

### `validate_port_data(port_data: dict) -> bool`

Validate port data structure and content.

| Parameter | Type | Description |
|-----------|------|-------------|
| `port_data` | `dict` | Dictionary to validate |

**Returns:** `bool` — `True` if valid.

**Validation rules:**
- Must be a non-empty `dict` — an empty mapping is invalid
- Keys must be convertible to `int`
- Values must be `str`
- Port numbers must be in range 0–65535

## PortListSummary

`lanscape.PortListSummary`

Pydantic model returned by [`get_port_list_summaries()`](#get_port_list_summaries---listportlistsummary).

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Port list name (without the `.json` extension) |
| `count` | `int` | Number of ports in the list (`0` if the list's data is invalid) |

```python
summary = PortManager().get_port_list_summaries()[0]
print(summary.model_dump())
# {'name': 'small', 'count': 20}
```

## Example: Custom Port List with ScanConfig

```python
from lanscape import PortManager, ScanManager, ScanConfig

pm = PortManager()

# Create a focused port list for web servers
web_ports = {
    "80": "HTTP",
    "443": "HTTPS",
    "8080": "HTTP-Alt",
    "8443": "HTTPS-Alt",
    "3000": "Dev-Server",
    "5000": "Flask",
    "8000": "Django"
}
pm.create_port_list("web-servers", web_ports)

# Use it in a scan
sm = ScanManager()
config = ScanConfig(subnet="192.168.1.0/24", port_list="web-servers")
scan = sm.new_scan(config)
sm.wait_until_complete(scan.uid)

# Cleanup
pm.delete_port_list("web-servers")
```
