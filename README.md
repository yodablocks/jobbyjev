# jobbyjev

Give it a resume and a list of companies. It ranks the companies by how
likely the candidate is to get an interview, puts a confidence on each, and
names the mismatch when there is one. A local reproduction of Backdoor's
"picking the best company using Jev" demo, built on TypeSafe's Jev model.

```
python3 rank.py samples/sample_resume.md          # 400 companies, ~25 s, ~$0.03
python3 rank.py my_resume.pdf --limit 50          # a quick look
open out/report.html
```

## Which way round it runs

It ranks **companies**, for one candidate. You give it your own resume and it
tells you where your applications are worth spending. That is the direction it
was built for and the only one anyone has looked at it in.

**Do not turn it around and screen candidates with it.** Run many resumes past
one company and `would_interview` becomes a hiring filter, and it would be a
bad one. Three reasons, all measured rather than asserted:

- It is generous. The median `would_interview` across 400 companies was 0.80,
  and 88 cleared the 0.70 "likely" line. The demo this reproduces found one
  in 400. Something that says yes to a fifth of the world sorts nobody.
- Nobody has checked a single one of these probabilities against who actually
  got an interview. They are Jev's numbers about a resume and a company
  description, not evidence about a person.
- The companies it scores against are made up in the ways that matter. See
  the data note below.

A number nobody has validated, applied to somebody's job application, is worse
than no number, because it looks like it knows something.

Needs Python 3.12, `requests`, and a TypeSafe key in `TYPESAFE_API_KEY`
(or `.env`, see `.env.example`). PDF resumes need `pdftotext` (poppler).

## How it works

One Jev request per company. The state is `{candidate: {resume}, company:
{name, hq, stage, size, category, description, hiring_for, founder_led}}`
and every request carries the same six judgments (`questions.py`):

| id | type | judgment |
|---|---|---|
| `domain_fit` | Score 0..3 | does the candidate's past work match what the company builds |
| `role_fit` | Score 0..3 | does their discipline match a role in `hiring_for` |
| `stage_fit` | Score 0..3 | have they worked at employers of this stage and size |
| `would_interview` | Noul | would a recruiter here reach out |
| `location_ok` | Noul | is the stated location or preference compatible with the HQ |
| `mismatch` | Choice | the single biggest disqualifier, with an explicit `none` |

Code combines them (`questions.compose`): `fit` is a weighted mean of the
three Scores, `chance` is half `would_interview` and half `fit`, scaled by
`location_ok`. Confidence is the mean of the Score and Choice confidences.
A mismatch is only reported when the Choice confidence clears 0.5. The
weights and thresholds are constants at the top of `questions.py`; change
them and re-run, the response cache makes that free.

Why one request per company and not 40 companies per request: the
[jev-orderby-bench](https://github.com/yodablocks/jev-orderby-bench)
measurement found the same rows through a 40-rows-per-state layout fail the
ranking gate (pairwise inversion 0.171 against a 0.15 threshold) while one
row per request passes. Ranking is the whole product here.

## Output

`out/results.json` holds the summary and every company's raw signals.
`out/report.html` is a self-contained page: the company grid tinted by
chance with a red ring on every company over 50%, the signal meters for
the selected company, a sideways-scrolling shortlist of everything over
the line, and a full ranked table. Pass `--photo headshot.jpg` to put a
picture in the header; it is inlined, never copied into the repo. Logos come from Google's favicon endpoint, so the page
needs network for logos only.

## A first run

Sample resume (fictional payments backend engineer, Taipei) against all 400
companies, `jev-1.13.0`, 16 workers:

| checked | likely interview | mismatch flagged | avg chance | time | input tokens | cost |
|---|---|---|---|---|---|---|
| 400 | 88 | 90 | 0.55 | 22.7 s | 669k | $0.028 |

Top of the list: Modern Treasury, Column, Unit, Melio, Increase, XREX,
Mercury, Supabase. Bottom: the semiconductor companies, all flagged as a
discipline mismatch. That is the order a person would give.

## What it is not

- **Generous on "would interview".** The median `would_interview`
  probability across the 400 was 0.80, so half the companies come out as
  plausible and 88 clear the 0.70 "likely" line. Backdoor's demo shows one
  "would hire" out of 400. Either raise `LIKELY_THRESHOLD`, or add the
  signal this build lacks: live openings. Without a posting to match
  against, "would a recruiter reach out" is answered about the company in
  general, and most companies hire backend engineers in general.

- **Not calibrated on hiring outcomes.** The probabilities are Jev's, and
  nobody has checked them against who actually got interviews. The same
  bench above found Jev underconfident on easy labels and failing four of
  six gates on a hard graded-relevance probe. Treat the order as a
  shortlist generator, not a prediction.
- **Nothing in the company data was researched.** `data/companies.json` is
  400 well-known tech companies written from a language model's general
  knowledge on 2026-09-17. No entry was sourced or checked against any
  company's own material. `stage`, `size`, `category`, `hiring_for` and
  `founder_led` are impressions rather than facts, and some of them are
  certainly wrong. Do not quote an entry as a fact about the company it
  names, and do not read anything into which companies are present. The file
  says all of this in its own `_provenance` record, because a JSON file gets
  copied and loaded by things that never read a README. It also has no job
  postings, so the demo's "they're hiring now" signal has no equivalent
  here. Replace it with sourced data before any answer matters.
- **English only, effectively.** Jev's accuracy on Chinese-language resumes
  is documented as lower. Translate first.
- **Resume text is sent to TypeSafe.** Read their data terms before using a
  real resume.

## Files

- `rank.py` CLI and pipeline
- `questions.py` the six judgments and the composite policy
- `jev_client.py` HTTP client with retries and a SQLite response cache
- `report.py` HTML renderer
- `data/companies.json` the 400 companies
- `samples/sample_resume.md` a fictional resume so it runs out of the box
- `test_questions.py` offline tests, `python3 test_questions.py`

MIT licensed.
