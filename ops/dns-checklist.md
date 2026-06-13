# DNS & deliverability checklist (do these BEFORE sending real mail)

| Record | Example | Why |
|---|---|---|
| A | mail.example.com -> your.ip | host identity |
| PTR | your.ip -> mail.example.com | reverse DNS **must** match HELO or you're spam |
| MX | example.com MX 10 mail.example.com | inbound routing |
| SPF (TXT) | `v=spf1 mx -all` | who may send for the domain |
| DKIM (TXT) | mail._domainkey.example.com -> from `rspamadm dkim_keygen` | cryptographic signing |
| DMARC (TXT) | `_dmarc` -> `v=DMARC1; p=none; rua=mailto:dmarc@example.com` | policy + reports; tighten to quarantine/reject after ~2 weeks of clean reports |
| MTA-STS / TLS-RPT | optional, after things are stable | enforce TLS to you |

Sanity checks: send to a Gmail address and "Show original" (SPF/DKIM/DMARC
must all be PASS); score 10/10 on mail-tester.com; verify port 25 outbound
isn't blocked by your provider (`nc -vz gmail-smtp-in.l.google.com 25`) —
if it is, set RELAYHOST in .env to a smarthost (SES, Mailgun, etc.).
