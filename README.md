# Sender Guard

Know the day a sending domain breaks. Sender Guard checks SPF, DKIM, DMARC and MX for your sending domains and reports what changed since the last run: an SPF record that crossed the 10-lookup limit, a DMARC policy that was weakened, a DKIM key that disappeared.

It is free for up to 3 domains and needs no account.

## Use it as a GitHub Action

1. Add a `domains.txt` file to your repository, one domain per line.
2. Copy [`.github/workflows/example.yml`](.github/workflows/example.yml) to `.github/workflows/sender-guard.yml`.

The workflow runs daily, keeps the last known state in `.sender-guard/state.json`, and opens an issue when something changed. Add a `SLACK_WEBHOOK_URL` secret to get the same text in Slack.

For more than 3 domains, add a pass as the `SENDER_GUARD_PASS` secret. Passes last 30 days: see <https://verifypulse-seven.vercel.app/tools/sender-guard#pass>.

## Use it from an AI agent (MCP)

Remote server, Streamable HTTP, no key: `https://verifypulse-seven.vercel.app/mcp`

| Tool | What it does |
|---|---|
| `inspect_domain_dns` | Full report for one domain |
| `audit_sending_domains` | Grade, SPF lookup count, DMARC policy and DKIM status for up to 3 domains |
| `monitor_sending_domains` | What changed since the snapshots you pass back |
| `flatten_spf` | TXT records that replace SPF includes with IP ranges |
| `verify_email` | Address check, $0.01 per call over x402 |

Claude Code:

```bash
claude mcp add --transport http sender-guard https://verifypulse-seven.vercel.app/mcp
```

## Use it over HTTP

```bash
curl -s https://verifypulse-seven.vercel.app/v1/guard/audit \
  -H "Content-Type: application/json" \
  -d '{"domains": ["yourdomain.com"]}'
```

Full endpoint list: <https://verifypulse-seven.vercel.app/llms.txt>

## What it checks

- **SPF**: every include is expanded the way a receiving server does it, so the DNS lookup count is the real one against the limit of 10, including void lookups.
- **DMARC**: the policy that applies to the domain, including one inherited from the parent domain.
- **DKIM**: keys published under the selectors large providers use, with key size. A selector it cannot guess is reported as not found, never as missing.
- **MX**: the hosts that receive replies and bounces.

## What it does not do

It reads public DNS only. It does not send email, does not confirm that an individual inbox exists, and does not process DMARC aggregate reports.

## Run the script yourself

`sender_guard.py` uses only the Python standard library.

```bash
python sender_guard.py domains.txt state.json
```

Exit code 0 means no critical change, 1 means at least one critical change, 2 means it could not run.

## License

MIT
