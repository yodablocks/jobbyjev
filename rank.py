#!/usr/bin/env python3
"""Rank companies by a candidate's chance of getting an interview, using Jev.

    python3 rank.py samples/sample_resume.md
    python3 rank.py my_resume.pdf --limit 50 --out out/me

One Jev request per company (never batched, see jev_client.py), all six
judgments in that request, composite computed in code (questions.py).
Writes <out>/results.json and <out>/report.html.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from jev_client import JevClient, NoAPIKey
from questions import QUESTIONS, build_state, compose
from report import render_html

HERE = Path(__file__).resolve().parent
DEFAULT_COMPANIES = HERE / "data" / "companies.json"
CACHE = HERE / ".data" / "cache.sqlite"


def read_resume(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            return subprocess.run(
                ["pdftotext", "-layout", str(path), "-"], check=True,
                capture_output=True, text=True,
            ).stdout
        except FileNotFoundError:
            sys.exit("pdftotext not found (brew install poppler), or pass a .md/.txt resume")
    return path.read_text()


def score_company(client: JevClient, resume: str, company: dict, use_cache: bool) -> dict:
    response = client.ask(build_state(resume, company), QUESTIONS, use_cache=use_cache)
    composed = compose(response["answers"])
    return {
        "id": company["id"],
        "name": company["name"],
        "domain": company.get("domain"),
        "hq": company.get("hq"),
        "stage": company.get("stage"),
        "category": company.get("category"),
        "size": company.get("size"),
        "founder_led": company.get("founder_led"),
        "hiring_for": company.get("hiring_for", []),
        **composed,
        "model": response.get("model"),
        "input_tokens": response.get("usage", {}).get("input_tokens"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("resume", type=Path, help=".md, .txt or .pdf")
    ap.add_argument("--companies", type=Path, default=DEFAULT_COMPANIES)
    ap.add_argument("--out", type=Path, default=HERE / "out")
    ap.add_argument("--limit", type=int, default=None, help="only the first N companies")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--model", default="jev-latest")
    ap.add_argument("--no-cache", action="store_true", help="re-query even if cached")
    ap.add_argument("--top", type=int, default=10, help="rows to print")
    args = ap.parse_args()

    resume = read_resume(args.resume).strip()
    if not resume:
        sys.exit(f"{args.resume} is empty")
    companies = json.loads(args.companies.read_text())
    if args.limit:
        companies = companies[: args.limit]

    client = JevClient(CACHE, model=args.model)
    results: list[dict] = []
    errors: list[tuple[str, str]] = []
    started = time.time()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(score_company, client, resume, c, not args.no_cache): c
                for c in companies
            }
            for i, fut in enumerate(as_completed(futures), 1):
                c = futures[fut]
                try:
                    results.append(fut.result())
                except NoAPIKey as e:
                    sys.exit(str(e))
                except Exception as e:  # keep going; report at the end
                    errors.append((c["name"], str(e)[:120]))
                print(f"\r  checked {i}/{len(companies)}", end="", flush=True)
    finally:
        print()
    elapsed = time.time() - started

    results.sort(key=lambda r: (-r["chance"], -r["confidence"], r["name"]))
    for rank, r in enumerate(results, 1):
        r["rank"] = rank

    likely = sum(r["likely_interview"] for r in results)
    mismatched = sum(1 for r in results if r["mismatch"])
    summary = {
        "resume": str(args.resume),
        "model": args.model,
        "checked": len(results),
        "total": len(companies),
        "likely_interview": likely,
        "mismatched": mismatched,
        "avg_chance": round(sum(r["chance"] for r in results) / max(len(results), 1), 3),
        "elapsed_s": round(elapsed, 1),
        "requests": client.usage.requests,
        "cache_hits": client.usage.cache_hits,
        "input_tokens": client.usage.input_tokens,
        "cost_usd": round(client.usage.cost_usd, 5),
        "errors": errors,
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=1, ensure_ascii=False)
    )
    (args.out / "report.html").write_text(render_html(summary, results, resume))

    print(f"\n{'#':>3}  {'company':<22} {'chance':>6} {'conf':>5}  {'mismatch':<10} hq")
    for r in results[: args.top]:
        print(f"{r['rank']:>3}  {r['name'][:22]:<22} {r['chance']:>6.2f} {r['confidence']:>5.2f}  "
              f"{(r['mismatch'] or '-'):<10} {r['hq']}")
    print(
        f"\nchecked {summary['checked']}/{summary['total']}  likely interview {likely}  "
        f"mismatched {mismatched}  avg chance {summary['avg_chance']}  "
        f"time {elapsed:.1f}s  cost ${summary['cost_usd']:.5f} "
        f"({client.usage.requests} requests, {client.usage.cache_hits} cached)"
    )
    if errors:
        print(f"\n{len(errors)} companies failed:")
        for name, err in errors[:10]:
            print(f"  {name}: {err}")
    print(f"\nreport: {args.out / 'report.html'}")


if __name__ == "__main__":
    main()
