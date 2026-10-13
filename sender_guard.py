#!/usr/bin/env python3
"""
Sender Guard runner: monitor the email authentication of a list of sending domains.

Standard library only. Run it on a schedule (the bundled GitHub Actions workflow runs it
daily). It keeps the last known state in a JSON file and reports only what changed.

  SENDER_GUARD_PASS   your pass (not needed for 3 domains or fewer)
  SLACK_WEBHOOK_URL   optional: Slack-compatible webhook that receives the alert text
  SENDER_GUARD_API    optional: API base URL

Usage: python sender_guard.py [domains.txt] [state.json]
Exit code 0 = no critical change, 1 = at least one critical change, 2 = could not run.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = os.environ.get("SENDER_GUARD_API", "https://verifypulse-seven.vercel.app").rstrip("/")
BATCH = 10


def post(url, payload, headers=None):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "sender-guard-runner/1.0", **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def main():
    domains_file = sys.argv[1] if len(sys.argv) > 1 else "domains.txt"
    state_file = sys.argv[2] if len(sys.argv) > 2 else ".sender-guard/state.json"
    guard_pass = os.environ.get("SENDER_GUARD_PASS", "").strip()

    with open(domains_file, encoding="utf-8") as f:
        domains = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    state = {}
    if os.path.exists(state_file):
        with open(state_file, encoding="utf-8") as f:
            state = json.load(f)

    changes, pending = [], []
    for start in range(0, len(domains), BATCH):
        batch = domains[start:start + BATCH]
        try:
            result = post(
                f"{API}/v1/guard/diff",
                {"domains": batch, "previous": {d: state[d] for d in batch if d in state}},
                {"X-Guard-Pass": guard_pass} if guard_pass else {},
            )
        except urllib.error.HTTPError as e:
            print(f"API refused the request ({e.code}): {e.read().decode()[:300]}", file=sys.stderr)
            return 2
        except Exception as e:  # network trouble: keep the old state for this batch and carry on
            print(f"Batch starting at {batch[0]} failed: {e}", file=sys.stderr)
            pending.extend(batch)
            continue
        state.update(result["snapshots"])
        changes.extend(result["changes"])
        pending.extend(result["pending"])

    os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, sort_keys=True)

    lines = [f"[{c['severity'].upper()}] {c['domain']}: {c['message']}" for c in changes]
    summary = "\n".join(lines) if lines else f"No changes across {len(domains)} domains."
    if pending:
        summary += f"\nNot checked this run (DNS slow, will retry): {', '.join(pending)}"
    print(summary)

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write(f"changed={'true' if lines else 'false'}\n")
        with open("sender-guard-report.txt", "w", encoding="utf-8") as f:
            f.write(summary + "\n")

    webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if webhook and lines:
        try:
            post(webhook, {"text": "Sender Guard: authentication changes detected\n" + summary})
        except Exception as e:
            print(f"Webhook delivery failed: {e}", file=sys.stderr)

    return 1 if any(c["severity"] == "critical" for c in changes) else 0


if __name__ == "__main__":
    sys.exit(main())
