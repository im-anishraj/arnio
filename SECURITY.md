# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Arnio, please report it responsibly by emailing:

**anishrajyadav97@gmail.com**

Subject line:

```text
ARNIO SECURITY
```

Please include:
- Description of the issue
- Steps to reproduce
- Potential impact
- Affected files/components
- Proof of concept (if available)

Please do not publicly disclose security vulnerabilities until they have been reviewed and addressed.

---

## Scope

The following security-related issues are considered in scope for Arnio:

- CSV parsing crashes or malformed CSV handling
- File path traversal vulnerabilities in `read_csv` or `scan_csv`
- Memory exhaustion or denial-of-service through crafted inputs
- Unsafe file handling or unintended file access
- Crashes caused by malformed datasets
- Security issues affecting CLI/API behavior

---

## Out of Scope

The following are generally considered out of scope:

- Feature requests
- Performance optimizations without security impact
- Style or formatting issues
- Documentation typos
- Non-security-related crashes
- Third-party dependency vulnerabilities without direct exploitability in Arnio

---

## Responsible Disclosure

We appreciate responsible disclosure and will review all valid reports as quickly as possible.