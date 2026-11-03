# Scribe

Local AI lab documentation pipeline. Paste raw terminal output, and Scribe uses a local large language model (via Ollama) to turn it into a structured lab note: observation, lesson learned, suggested next commands, tags, and a one-line interview bullet.

Every run produces two versions:

- **Private note** saved to an Obsidian vault with the full raw output and infrastructure detail. It is never committed.
- **Public note** saved to `github-ready/`, with raw output stripped and sensitive details redacted, safe to publish.

Nothing leaves the machine: the model runs locally.

## How It Works

1. Enter a lab name and objective, then paste terminal output.
2. Scribe sends it to a local model (default `qwen2.5:14b`) through Ollama.
3. The response is written into a private Obsidian note with YAML frontmatter.
4. A sanitizer builds the public version and prints a redaction report.
5. An **approval gate** lists every file written and the suggested git commands. Nothing is committed or pushed automatically.

## Sanitizer

The public note is scrubbed before it is written:

| Redacted | Replaced with |
| --- | --- |
| Private IPv4 addresses (10.x, 172.16–31.x, 192.168.x) | `<internal-ip>` |
| Known lab hostnames | `<lab-host>` |
| MAC addresses | `<mac-address>` |
| Email addresses | `<email>` |
| WireGuard interface names (`wg0`, ...) | `<vpn-interface>` |
| Strings of 32+ characters that look like tokens | `<redacted-token>` |

The token rule can also match hashes and UUIDs, so the redaction report flags it for manual review.

## Requirements

- Python 3
- [Ollama](https://ollama.com) running locally with the model pulled: `ollama pull qwen2.5:14b`
- Python client: `pip install -r requirements.txt`
- An Obsidian vault at `~/Documents/Lab Work/02 - Lab Notes` (path set by `VAULT_ROOT` in `scribe.py`)

## Usage

```bash
python scribe.py
```

Settings at the top of `scribe.py`:

- `MODEL`: which Ollama model to use
- `DRY_RUN`: preview output without writing files
- `SANITIZE_FOR_PUBLIC`: generate the public version
- `LAB_HOSTNAMES`: hostnames to redact

## Lab Index

> Sanitized public lab notes, appended automatically by Scribe.

- [Lab Test Sanitization](github-ready/Public_2026-05-17_2229_Lab_Test_Sanitization.md)
