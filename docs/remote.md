# Remote CSV Input

`read_csv`, `scan_csv`, and `read_csv_chunked` accept HTTP and HTTPS URLs
in addition to local filesystem paths and file-like objects.  No extra
packages are required for HTTP/HTTPS — Arnio uses Python's built-in
`urllib` module.

## Supported input modes

| Input type | Example | Requires |
|---|---|---|
| Local path | `ar.read_csv("data.csv")` | nothing |
| `os.PathLike` | `ar.read_csv(Path("data.csv"))` | nothing |
| File-like object | `ar.read_csv(io.StringIO(...))` | nothing |
| HTTP / HTTPS URL | `ar.read_csv("https://example.com/data.csv")` | nothing (stdlib) |
| S3 URL | `ar.read_csv("s3://bucket/data.csv")` | `arnio[s3]` *(planned)* |
| GCS URL | `ar.read_csv("gs://bucket/data.csv")` | `arnio[gcs]` *(planned)* |
| Azure Blob URL | `ar.read_csv("az://container/data.csv")` | `arnio[azure]` *(planned)* |

## Basic usage

```python
import arnio as ar

# Read a CSV file directly from the web
frame = ar.read_csv("https://example.com/data.csv")

# Inspect schema without downloading the full file body
schema = ar.scan_csv("https://example.com/large.csv")

# Stream a remote CSV in chunks
for chunk in ar.read_csv_chunked("https://example.com/big.csv", chunksize=10_000):
    process(chunk)
```

All keyword arguments accepted by the local-path variants (`delimiter`,
`has_header`, `usecols`, `nrows`, `encoding`, etc.) work identically with
URL inputs.

## Error handling

```python
from arnio.exceptions import RemoteReadError

try:
    frame = ar.read_csv("https://example.com/data.csv")
except RemoteReadError as e:
    print(f"Fetch failed: {e}")
    print(f"URL: {e.url}")
    print(f"HTTP status: {e.status_code}")  # None for network-level failures
```

`RemoteReadError` is raised for:

- Non-2xx HTTP responses (e.g. 404 Not Found, 403 Forbidden)
- Network-level failures (DNS resolution failure, connection refused, timeout)
- Response body that cannot be decoded as UTF-8

The exception exposes two attributes:

| Attribute | Type | Description |
|---|---|---|
| `url` | `str` | The URL that failed |
| `status_code` | `int \| None` | HTTP status code, or `None` for network errors |

## Cloud provider schemes (planned)

Passing an `s3://`, `gs://`, `az://`, `abfs://`, or `abfss://` URL raises
a `ValueError` with an actionable install hint:

```
ValueError: Cloud scheme 's3' is not yet supported by arnio.
Install the optional extra when available: pip install "arnio[s3]"
```

This ensures that users get a clear message rather than a cryptic error
from the C++ backend when support arrives in a follow-up release.

## Security and credential notes

- **HTTP/HTTPS**: Arnio passes a `User-Agent: arnio/read_csv` header. No
  authentication is performed. If the server requires credentials, use a
  pre-signed URL or download the file manually.
- **Timeout**: Requests time out after 30 seconds. There is no retry logic;
  implement retries in your calling code if needed.
- **Content validation**: The response body is expected to be UTF-8 encoded
  CSV text. Non-UTF-8 responses raise `RemoteReadError` with a descriptive
  message.
- **Redirects**: `urllib` follows redirects by default (up to 10 hops).
- **TLS/SSL**: Standard Python SSL certificate verification applies. If you
  need to disable it (e.g. for internal CAs), pre-fetch the file manually
  and pass an `io.StringIO` instead.
