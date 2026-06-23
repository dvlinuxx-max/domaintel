# domaintel

Domain registration lookup over RDAP, the modern JSON-based successor to WHOIS.
Reports the registrar, registration/expiry/update dates, status codes, and
nameservers, plus a computed domain age and days-to-expiry.

## Usage

```bash
python domaintel.py example.com
python domaintel.py example.com --json
```

## Example

```
$ python domaintel.py github.com

domaintel github.com

  registrar   MarkMonitor Inc.
  registered  2007-10-09T18:20:50Z  (6832 days old)
  expires     2026-10-09T18:20:50Z  (108 days)
  updated     2024-09-07T09:16:32Z
  status      client delete prohibited, client transfer prohibited, ...
  nameservers
    dns1.p08.nsone.net
    ...
```

## Why RDAP instead of WHOIS

WHOIS is unstructured text that varies by registry and needs port 43 sockets
and per-TLD server discovery. RDAP returns structured JSON over HTTPS, with a
public bootstrap (`rdap.org`) that routes each domain to the correct registry.
domaintel follows that bootstrap and parses the standard RDAP objects.

## How it works

```
domaintel.py
  fetch_rdap       GET rdap.org/domain/<domain> (bootstrap -> registry RDAP)
  registrar_name   pull the entity with role "registrar" from its vCard
  summarize        events -> dates, nameservers, status
```

## Requirements

Python 3.9+, network access. No third-party packages.

## License

MIT
