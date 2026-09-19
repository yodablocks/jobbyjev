# Wen-Hao Lin

Taipei, Taiwan. Open to remote roles and to relocating within Asia or to the US.
wenhao.lin@example.com

## Summary

Backend and infrastructure engineer, seven years. Built and ran the payments
and ledger services at a Series B fintech, then the developer platform at a
growth-stage API company. Comfortable owning a service end to end: design,
Go or TypeScript implementation, Postgres schema, on-call, and the docs
developers read. Have shipped public SDKs and written the launch posts for them.

## Experience

### Senior Software Engineer, Developer Platform — Pave (growth stage, ~300 people)
2024 — present, remote

- Own the public REST API and the TypeScript and Python SDKs used by ~2,000
  integrators. Cut p99 latency of the core endpoints from 900 ms to 180 ms by
  moving hot paths off the ORM and adding a read replica.
- Designed the webhook delivery system (at-least-once, signed payloads,
  replay UI). Zero lost events across 40M deliveries in the last year.
- Wrote the API reference and quickstarts; support tickets about auth dropped
  by half after the rewrite.

### Software Engineer, Payments — Kryptogo (Series B, ~60 people)
2021 — 2024, Taipei

- Built the double-entry ledger service in Go on Postgres that settles card
  and bank-transfer payments for merchants in Taiwan and Japan.
- Led the PCI DSS scoping for the card vault; passed the first audit.
- Two years of on-call for the payment gateway; wrote the runbooks the team
  still uses.

### Software Engineer — Appier
2019 — 2021, Taipei

- Data pipeline work in Python and Spark for the ad-targeting product.
  Migrated batch jobs from cron to Airflow.

## Skills

Go, TypeScript, Python, Postgres, Redis, Kafka, Kubernetes, AWS, Terraform.
Payments, ledgers, API design, SDK design, developer documentation.

## Education

BS Computer Science, National Taiwan University, 2019.
