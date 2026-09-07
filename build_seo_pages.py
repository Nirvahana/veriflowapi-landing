#!/usr/bin/env python3
"""Generate the marketing content pages for veriflowapi.com.

History: this script used to emit 24 pages from one template (a page per state, per
profession and per use case). They shared 93-100% of their vocabulary and each carried
~190 unique words, which is the classic doorway / thin-content pattern: the pages competed
with each other for the same queries instead of ranking, and Google rotated which one it
showed. They are now consolidated into four substantial pages, and every retired URL is
served as a canonical + meta-refresh redirect so no indexed URL or inbound link 404s.

Output:
    coverage.html                     pillar page: per-state detail + role matrix
    for/telehealth.html               genuinely distinct use-case pages
    for/credentialing-software.html
    for/healthcare-staffing.html
    verify/seo.css                    shared stylesheet
    <retired urls>                    redirect stubs -> the page that replaced them
    sitemap.xml                       canonical pages only (stubs excluded)

    python build_seo_pages.py
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://veriflowapi.com"
SIGNUP = "https://app.veriflowapi.com/signup"
DOCS = "https://docs.veriflowapi.com"

# --- Per-state substance -----------------------------------------------------
# Everything here is specific to how we actually verify that state: the board, how the data
# is obtained, how fresh it is, and the honest caveats. This is the material the old
# template threw away in favour of swapping a state name.

STATES = [
    dict(slug="california", abbr="CA", name="California",
         board="Department of Consumer Affairs (DCA)", method="Monthly mirror",
         refresh="Refreshed the 1st of each month", records="489,000 licensees",
         discipline="Not yet",
         detail="We mirror the DCA's public licensee files across six boards: the Medical "
                "Board, Osteopathic Medical Board, Board of Psychology, Board of Behavioral "
                "Sciences (LCSW, LMFT, LPCC), Physical Therapy Board and Board of "
                "Occupational Therapy. Each check returns the license number, license type, "
                "issuing board, status and expiry date.",
         caveat="California's public files carry status and expiry but no disciplinary "
                "history, and the Speech-Language Pathology board's file is published empty, "
                "so SLP is not covered in California yet. Both arrive through the DCA's "
                "iServices API. Because the source is monthly rather than daily, every "
                "certificate records the exact as-of date so you can see how current a "
                "result is."),
    dict(slug="texas", abbr="TX", name="Texas",
         board="Texas Medical Board (TMB)", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="Texas publishes no bulk file, so we query the Texas Medical Board's public "
                "verification portal at the moment you ask and cache the answer for 24 hours. "
                "It covers physicians (MD/DO), physician assistants, acupuncturists and the "
                "other license types TMB issues, returning license number, type, status, "
                "expiry and disciplinary restrictions.",
         caveat="TMB lists training permits alongside full licenses, and a physician who "
                "trained in Texas often holds both. We resolve to the full license rather "
                "than an expired residency permit, so a practising physician is never "
                "reported as a lapsed trainee."),
    dict(slug="newyork", abbr="NY", name="New York",
         board="Office of the Professions (OP)", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Partial",
         detail="New York is search-only, so we query the Office of the Professions at "
                "verification time. It covers physicians, psychologists, social workers, "
                "mental health counsellors, marriage and family therapists, PT, OT and SLP.",
         caveat="A New York license does not expire; the triennial <em>registration</em> "
                "does. We therefore return registration status and the registered-through "
                "date rather than an expiry, and map an unregistered licensee to expired. "
                "For non-physician professions the Office publishes enforcement actions and "
                "we return them; physician discipline sits with the Department of Health's "
                "Office of Professional Medical Conduct, a separate source."),
    dict(slug="pennsylvania", abbr="PA", name="Pennsylvania",
         board="Pennsylvania Licensing System (PALS)", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="We query PALS across all seven health boards in a single pass: Medicine, "
                "Osteopathic Medicine, Psychology, Social Workers / MFTs / Professional "
                "Counselors, Physical Therapy, Occupational Therapy and Speech-Language "
                "Pathology. Each result carries the license number, type, issuing board, "
                "status, issue and expiry dates, and the licensee's disciplinary actions.",
         caveat="PALS returns every license a person has ever held, and often lists an "
                "expired graduate training permit ahead of the active MD license. We rank "
                "matches so an active, full license wins over a lapsed permit. PALS also "
                "matches names by prefix, so we require an exact surname before confirming "
                "anyone."),
    dict(slug="ohio", abbr="OH", name="Ohio",
         board="eLicense Ohio", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="Ohio consolidates its boards on eLicense, which we query live across the "
                "State Medical Board, Board of Psychology, the Counselor, Social Worker and "
                "Marriage &amp; Family Therapist Board, the OT/PT/AT Board and the Speech and "
                "Hearing Professionals Board. eLicense Ohio states that the Joint Commission "
                "and NCQA accept its online status as primary-source verification.",
         caveat="Ohio's headline status is coarse (Active, Inactive, Closed); the meaningful "
                "detail lives in a sub-status such as Expired, Lapsed, Suspended or Retired. "
                "We read the sub-status and normalise it, so a credential that reads active "
                "upstream but has actually lapsed is reported as expired."),
    dict(slug="michigan", abbr="MI", name="Michigan",
         board="Dept. of Licensing and Regulatory Affairs (LARA)", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Partial",
         detail="Michigan publishes no bulk licensee file, so we query LARA's public MiPLUS "
                "portal at the moment you ask and cache the answer for 24 hours. It covers "
                "medical doctors and osteopathic physicians, psychologists, master's and "
                "bachelor's social workers, professional counselors, marriage and family "
                "therapists, physical therapists, occupational therapists and "
                "speech-language pathologists, returning licence number, type, status and "
                "expiry date.",
         caveat="Michigan labels a licence whose expiry has already passed but which is "
                "still inside the renewal window as &ldquo;Active - In Late Renewal&rdquo;. "
                "We report that as expired, because the date has passed and practice is not "
                "authorised. LARA also publishes no NPI, so Michigan matches on name alone, "
                "and the portal shows current sanctions such as probation or suspension "
                "without the order narrative, which LARA issues separately in monthly "
                "disciplinary reports."),
    dict(slug="florida", abbr="FL", name="Florida",
         board="Department of Health, Medical Quality Assurance (MQA)",
         method="Daily mirror", refresh="Refreshed daily",
         records="1.5 million licensees", discipline="Yes",
         detail="We mirror Florida's full MQA licensure file every day: roughly 1.5 million "
                "licensees across more than 180 professions. Each record carries the license "
                "number, profession, status, expiry, issue date, city and county.",
         caveat="Florida operates dedicated out-of-state telehealth registration categories "
                "for several professions, which appear in the file as their own license "
                "types. That matters if you onboard clinicians who treat Florida patients "
                "from another state."),
    dict(slug="illinois", abbr="IL", name="Illinois",
         board="Department of Financial and Professional Regulation (IDFPR)",
         method="Daily mirror", refresh="Refreshed daily",
         records="4.2 million records", discipline="Yes",
         detail="We mirror the official IDFPR licensee database daily. The Joint Commission "
                "and NCQA recognise the IDFPR lookup as an approved primary source, so an "
                "Illinois verification stands on its own in an accreditation file.",
         caveat="Illinois records a single social-work category rather than breaking out the "
                "clinical (LCSW) designation the way Florida, Washington and Connecticut do, "
                "so treat an Illinois social-work result as the licence itself rather than "
                "proof of the clinical specialty."),
    dict(slug="washington", abbr="WA", name="Washington",
         board="Department of Health (DOH)", method="Daily mirror",
         refresh="Refreshed daily", records="2.4 million credentials", discipline="Yes",
         detail="Washington's health-care provider credential file is mirrored daily and is "
                "unusually broad: physicians, nurses and pharmacists alongside the full "
                "behavioural and allied health set, including mental health counsellors, "
                "social workers, marriage and family therapists, psychologists, OT, PT and "
                "SLP.",
         caveat="Washington is one of the few states that licenses behavior analysts at "
                "state level, so a Washington-based BCBA's state credential can be verified "
                "here even though the national BACB certification itself is a separate "
                "registry we do not cover."),
    dict(slug="colorado", abbr="CO", name="Colorado",
         board="Department of Regulatory Agencies (DORA)", method="Daily mirror",
         refresh="Refreshed daily", records="1.6 million records",
         discipline="Status + expiry",
         detail="Colorado's professional and occupational licence data is mirrored daily "
                "from the state's open-data service, covering physicians, psychologists, "
                "clinical social workers, professional counsellors, marriage and family "
                "therapists, PT, OT and SLP.",
         caveat="DORA encodes the profession as a licence-type prefix rather than a readable "
                "name, which we decode on ingest so results come back as a role you can act "
                "on. Colorado returns status and expiry; its disciplinary feed is a "
                "near-term addition."),
    dict(slug="connecticut", abbr="CT", name="Connecticut",
         board="Department of Consumer Protection (DCP)", method="Daily mirror",
         refresh="Refreshed daily", records="2.6 million credentials",
         discipline="Status + expiry",
         detail="Connecticut's licence and credential data is mirrored daily, covering the "
                "health professions alongside the state's other regulated occupations.",
         caveat="Connecticut publishes one combined name field rather than separate first and "
                "last names, and reuses credential numbers across record types. We split the "
                "name and deduplicate to one canonical row per credential at ingest so "
                "lookups resolve to a single person. Connecticut returns status and expiry; "
                "discipline is a near-term addition."),
    dict(slug="alabama", abbr="AL", name="Alabama",
         board="Board of Medical Examiners (BME)", method="Daily roster",
         refresh="Refreshed daily", records="60,000 licensees", discipline="Yes",
         detail="We take the Alabama Board of Medical Examiners' roster of active licences "
                "daily. It is primary-source verified and covers MD, DO and CRNP/CNM, with "
                "the supervising physician recorded where the credential requires one.",
         caveat="The Alabama roster lists currently active licences, so it confirms present "
                "standing rather than reconstructing a lapsed licence's history."),
]

ALL_CLINICAL = ["FL", "WA", "IL", "CO", "CT", "NY", "PA", "OH", "CA", "MI"]
NO_CA = [s for s in ALL_CLINICAL if s != "CA"]
ROLES = [
    ("Physician (MD / DO)", "State medical or osteopathic licence",
     ["TX", "FL", "IL", "WA", "CO", "CT", "AL", "NY", "PA", "OH", "CA", "MI"]),
    ("Psychologist / Neuropsychologist", "Licensed Psychologist", ALL_CLINICAL),
    ("Licensed Clinical Social Worker", "LCSW", ALL_CLINICAL),
    ("Professional / Mental Health Counselor", "LPC, LPCC or LMHC", ALL_CLINICAL),
    ("Marriage and Family Therapist", "LMFT", ALL_CLINICAL),
    ("Physical Therapist", "PT", ALL_CLINICAL),
    ("Occupational Therapist", "OT", ALL_CLINICAL),
    ("Speech-Language Pathologist", "SLP", NO_CA),
]
ALL_ABBR = ["TX", "FL", "IL", "WA", "CO", "CT", "AL", "NY", "PA", "OH", "CA", "MI"]

# --- Retired URLs -> what replaced them ---------------------------------------
REDIRECTS: dict[str, str] = {}
# Only states that HAD a retired per-state page get a redirect stub. A state added after the
# consolidation (Michigan) never had one, and inventing a stub would re-create the thin-page
# pattern the consolidation removed.
_RETIRED_STATE_PAGES = {"california", "texas", "newyork", "pennsylvania", "ohio", "florida",
                        "illinois", "washington", "colorado", "connecticut", "alabama"}
for _s in STATES:
    if _s["slug"] in _RETIRED_STATE_PAGES:
        REDIRECTS[f"verify/{_s['slug']}-license-verification.html"] =             f"/coverage.html#{_s['slug']}"
for _p in ("physician", "psychologist", "clinical-social-worker", "professional-counselor",
           "marriage-family-therapist", "physical-therapist", "occupational-therapist",
           "speech-language-pathologist"):
    REDIRECTS[f"verify/{_p}-license-verification.html"] = "/coverage.html#professions"
REDIRECTS["for/provider-onboarding.html"] = "/for/credentialing-software.html"
REDIRECTS["for/marketplaces.html"] = "/for/healthcare-staffing.html"

CSS = """/* Shared styles for VeriflowAPI content pages. */
:root{--ink:#0f1117;--ink-muted:#6b7080;--surface:#fafaf8;--surface-2:#f4f3ef;
--accent:#1a4fff;--accent-light:#e8eeff;--accent-dark:#1238cc;--success:#0ea561;
--warn:#d97706;--border:#e2e0d8;--code-bg:#0f1117;}
*{box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{margin:0;font-family:'DM Sans',system-ui,sans-serif;color:var(--ink);
background:var(--surface);line-height:1.65;-webkit-font-smoothing:antialiased;}
a{color:var(--accent);text-decoration:none;}
a:hover{text-decoration:underline;}
.wrap{max-width:880px;margin:0 auto;padding:0 24px;}
header.nav{border-bottom:1px solid var(--border);background:rgba(250,250,248,.92);
backdrop-filter:blur(8px);position:sticky;top:0;z-index:10;}
.nav .wrap{display:flex;align-items:center;justify-content:space-between;height:62px;}
.logo{font-family:'DM Serif Display',serif;font-size:1.35rem;color:var(--ink);}
.logo span{color:var(--accent);}
.cta{background:var(--accent);color:#fff;padding:.6rem 1.15rem;border-radius:7px;
font-weight:600;font-size:.9rem;display:inline-block;}
.cta:hover{background:var(--accent-dark);text-decoration:none;}
.cta-lg{padding:.85rem 1.6rem;font-size:1rem;}
h1{font-family:'DM Serif Display',serif;font-size:2.5rem;line-height:1.12;margin:.2em 0;}
h2{font-family:'DM Serif Display',serif;font-size:1.65rem;margin:1.8em 0 .5em;}
h3{font-size:1.05rem;margin:1.6em 0 .3em;}
.badge{display:inline-block;background:var(--accent-light);color:var(--accent-dark);
font-size:.78rem;font-weight:600;padding:.3rem .7rem;border-radius:100px;margin-bottom:1rem;}
.hero{padding:60px 0 34px;}
.hero p.sub{font-size:1.16rem;color:var(--ink-muted);max-width:660px;}
.hero .cta-lg{margin-top:1.3rem;}
.free{font-size:.85rem;color:var(--ink-muted);margin-top:.7rem;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin:1em 0;}
.card{background:#fff;border:1px solid var(--border);border-radius:12px;padding:20px;}
.card h3{margin:.1em 0 .35em;font-size:1.05rem;}
.card p{margin:0;color:var(--ink-muted);font-size:.95rem;}
pre{background:var(--code-bg);color:#e6e9f2;border-radius:12px;padding:20px;overflow-x:auto;
font-family:'DM Mono',ui-monospace,monospace;font-size:.82rem;line-height:1.6;}
pre .k{color:#8ab4ff;}pre .s{color:#8ce0a8;}pre .b{color:#ffb454;}pre .c{color:#6b7080;}
table{width:100%;border-collapse:collapse;margin:1em 0;font-size:.93rem;}
th,td{text-align:left;padding:.55rem .7rem;border-bottom:1px solid var(--border);}
th{font-size:.78rem;text-transform:uppercase;letter-spacing:.03em;color:var(--ink-muted);}
td.y{color:var(--success);font-weight:600;}td.n{color:var(--ink-muted);}
.state{background:#fff;border:1px solid var(--border);border-radius:12px;padding:22px 24px;margin:14px 0;}
.state h3{margin:0 0 .2em;font-size:1.15rem;font-family:'DM Serif Display',serif;}
.state .meta{font-size:.82rem;color:var(--ink-muted);margin-bottom:.7em;}
.state .caveat{background:var(--surface-2);border-left:3px solid var(--warn);
padding:.7rem .9rem;border-radius:0 8px 8px 0;font-size:.92rem;margin-top:.8em;}
.state .caveat strong{color:var(--warn);}
.faq details{border-bottom:1px solid var(--border);padding:.9em 0;}
.faq summary{font-weight:600;cursor:pointer;}
.faq p{color:var(--ink-muted);margin:.6em 0 0;}
.cta-band{background:var(--accent-light);border-radius:16px;padding:40px;text-align:center;margin:52px 0;}
.cta-band h2{margin-top:0;}
footer{border-top:1px solid var(--border);padding:32px 0;color:var(--ink-muted);font-size:.85rem;}
footer a{color:var(--ink-muted);}
.muted{color:var(--ink-muted);}
@media(max-width:640px){h1{font-size:1.95rem;}.hero{padding:38px 0 26px;}
table{font-size:.85rem;}th,td{padding:.45rem .4rem;}}
"""

SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>__TITLE__</title>
<meta name="description" content="__DESC__"/>
<link rel="canonical" href="__CANON__"/>
<meta property="og:title" content="__TITLE__"/>
<meta property="og:description" content="__DESC__"/>
<meta property="og:type" content="website"/>
<meta property="og:url" content="__CANON__"/>
<meta name="twitter:card" content="summary_large_image"/>
<link rel="icon" href="/favicon.svg"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/verify/seo.css"/>
<script type="application/ld+json">__JSONLD__</script>
</head>
<body>
<header class="nav"><div class="wrap">
  <a class="logo" href="/">Veri<span>flow</span>API</a>
  <a class="cta" href="__SIGNUP__">Start Free &rarr;</a>
</div></header>
<main class="wrap">
__BODY__
  <div class="cta-band">
    <h2>__CTA_H__</h2>
    <p class="muted" style="max-width:560px;margin:0 auto 1.2rem;">Start with 100 free verifications. No credit card. Read the <a href="__DOCS__/introduction">docs</a> or the <a href="__DOCS__/data-sources">source reference</a>.</p>
    <a class="cta cta-lg" href="__SIGNUP__">Create your account &rarr;</a>
  </div>
</main>
<footer><div class="wrap">
  &copy; 2026 SecureHealth AI LLC d/b/a Veriflow &middot;
  <a href="/">Home</a> &middot;
  <a href="/coverage.html">Coverage</a> &middot;
  <a href="/status.html">Status</a> &middot;
  <a href="__DOCS__/introduction">Docs</a> &middot;
  <a href="/terms.html">Terms</a> &middot;
  <a href="/privacy.html">Privacy</a>
</div></footer>
</body>
</html>
"""

STUB = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Moved &mdash; VeriflowAPI</title>
<link rel="canonical" href="__TARGET_ABS__"/>
<meta http-equiv="refresh" content="0; url=__TARGET__"/>
</head>
<body>
<p>This page has moved to <a href="__TARGET__">__TARGET_ABS__</a>.</p>
</body>
</html>
"""


def write(path: str, html: str) -> None:
    out = os.path.join(HERE, path)
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)


def faq_block(qas) -> str:
    items = "\n    ".join(
        f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in qas)
    return f'<section class="faq">\n    <h2>Common questions</h2>\n    {items}\n  </section>'


def page(*, path, title, desc, body, cta_h, qas) -> str:
    canon = f"{SITE}/{path}"
    data = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "name": title, "description": desc, "url": canon},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qas]}]}
    html = SHELL
    for key, val in {
        "__TITLE__": title, "__DESC__": desc, "__CANON__": canon,
        "__SIGNUP__": SIGNUP, "__DOCS__": DOCS, "__CTA_H__": cta_h,
        "__BODY__": body + "\n  " + faq_block(qas),
        "__JSONLD__": json.dumps(data),
    }.items():
        html = html.replace(key, val)
    write(path, html)
    return f"/{path}"


# --- Coverage pillar page ----------------------------------------------------

def coverage_page() -> str:
    summary = "".join(
        f'<tr><td><a href="#{s["slug"]}">{s["name"]}</a></td><td>{s["board"]}</td>'
        f'<td>{s["method"]}</td><td>{s["records"]}</td>'
        f'<td class="{"y" if s["discipline"] == "Yes" else "n"}">{s["discipline"]}</td></tr>'
        for s in STATES)

    details = "".join(
        f'<div class="state" id="{s["slug"]}">'
        f'<h3>{s["name"]} &mdash; {s["board"]}</h3>'
        f'<div class="meta">{s["method"]} &middot; {s["refresh"]} &middot; '
        f'Disciplinary data: {s["discipline"]}</div>'
        f'<p>{s["detail"]}</p>'
        f'<div class="caveat"><strong>Worth knowing:</strong> {s["caveat"]}</div>'
        f'</div>' for s in STATES)

    head = "".join(f"<th>{a}</th>" for a in ALL_ABBR)
    rows = "".join(
        f'<tr><td><strong>{name}</strong><br><span class="muted" '
        f'style="font-size:.85em">{lic}</span></td>'
        + "".join(f'<td class="{"y" if a in states else "n"}">'
                  f'{"&#10003;" if a in states else "&middot;"}</td>' for a in ALL_ABBR)
        + "</tr>" for name, lic, states in ROLES)

    body = f"""  <section class="hero">
    <div class="badge">12 states live &middot; updated September 2026</div>
    <h1>What VeriflowAPI actually verifies</h1>
    <p class="sub">Every state we cover, the board each result comes from, how fresh it is,
    and the specific limits of each source. Federal identity and exclusion screening runs
    nationwide on every check.</p>
    <a class="cta cta-lg" href="{SIGNUP}">Start free &rarr; 100 verifications</a>
    <div class="free">No credit card required.</div>
  </section>

  <section>
    <h2>Federal screening, all 50 states</h2>
    <p>Two federal checks run on every verification regardless of the state:</p>
    <div class="grid">
      <div class="card"><h3>NPPES identity</h3><p>Confirms the provider and NPI exist and the
      record is active, with name and credential. Refreshed daily.</p></div>
      <div class="card"><h3>OIG exclusions</h3><p>Whether the provider appears on the HHS
      exclusion list, with exclusion type and dates. Refreshed every 12 hours.</p></div>
    </div>
    <p>Exclusion matching deserves a note, because name-only matching is what produces false
    positives in this industry. Roughly 90% of exclusion records carry no NPI, so a common
    name can collide with an excluded stranger. We use the identifiers you supply to resolve
    it: a matching <code>npi</code> or <code>dob</code> confirms an exclusion, a
    <em>different</em> one rules that record out as a different person, and a name-only match
    is reported conservatively rather than silently cleared. Sending a date of birth is the
    single most effective way to avoid a false exclusion on a common name.</p>
  </section>

  <section>
    <h2>State coverage at a glance</h2>
    <table>
      <thead><tr><th>State</th><th>Board</th><th>How we get it</th><th>Scale</th>
      <th>Discipline</th></tr></thead>
      <tbody>{summary}</tbody>
    </table>
    <p class="muted">There are two shapes of source. A <strong>mirror</strong> means we hold
    a full copy of the state's published file and refresh it on a schedule, so lookups are
    instant. A <strong>live per-query</strong> state publishes no bulk file, so we query the
    board at the moment you ask and cache the result for 24 hours.</p>
  </section>

  <section>
    <h2>State by state</h2>
    {details}
  </section>

  <section id="professions">
    <h2>Which professions, in which states</h2>
    <p>We verify the underlying state licence. Board sub-certifications issued by national
    bodies rather than state boards &mdash; ABPN for psychiatry, ABPP or ABCN for clinical
    neuropsychology, BACB for behavior analysts &mdash; are separate national registries, so
    a psychiatrist is verified through their state medical licence and a neuropsychologist
    through their Licensed Psychologist licence.</p>
    <table>
      <thead><tr><th>Role</th>{head}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>

  <section>
    <h2>What happens outside these states</h2>
    <p>A state we do not cover returns <code>status: "unsupported_state"</code> with
    <code>verified: false</code>. Federal NPPES and OIG results are still returned, so you
    get real identity and exclusion signal everywhere and route only the state-licence
    portion to manual review. We do not guess, infer or fabricate a state result, because a
    wrong confirmation is worse in a credentialing file than an honest gap.</p>
    <p>Next on the roadmap: California disciplinary history and speech-language pathology
    through the DCA's iServices API, Georgia physicians, and FSMB national disciplinary data.
    If a state is blocking you, <a href="mailto:support@veriflowapi.com">tell us</a> &mdash;
    coverage is prioritised by what customers actually ask for.</p>
  </section>

  <section>
    <h2>One call, every source</h2>
    <pre><span class="c"># Federal identity + exclusions + the state board, in one request</span>
POST https://api.veriflowapi.com/v1/verify

{{
  <span class="k">"first_name"</span>: <span class="s">"Jane"</span>,
  <span class="k">"last_name"</span>: <span class="s">"Provider"</span>,
  <span class="k">"state"</span>: <span class="s">"PA"</span>,
  <span class="k">"npi"</span>: <span class="s">"1234567890"</span>,
  <span class="k">"dob"</span>: <span class="s">"1980-05-31"</span>
}}

<span class="c"># Response</span>
{{
  <span class="k">"verified"</span>: <span class="b">true</span>,
  <span class="k">"status"</span>: <span class="s">"active"</span>,
  <span class="k">"match_confidence"</span>: <span class="s">"high"</span>,
  <span class="k">"license_number"</span>: <span class="s">"MD123456"</span>,
  <span class="k">"expiry_date"</span>: <span class="s">"2027-12-31"</span>,
  <span class="k">"disciplinary_flags"</span>: <span class="b">false</span>,
  <span class="k">"oig_excluded"</span>: <span class="b">false</span>,
  <span class="k">"sources_checked"</span>: [<span class="s">"NPPES"</span>, <span class="s">"OIG"</span>, <span class="s">"PA Licensing System (PALS)"</span>],
  <span class="k">"certificate_hash"</span>: <span class="s">"sha256_..."</span>
}}</pre>
  </section>
"""
    return page(
        path="coverage.html",
        title="License Verification Coverage: 12 States, Board by Board | VeriflowAPI",
        desc="Every state VeriflowAPI verifies, the board each result comes from, how often "
             "it refreshes, and the honest limits of each source. Plus nationwide NPPES and "
             "OIG screening on every check.",
        body=body,
        cta_h="Verify a provider in any of these states",
        qas=[
            ("Which states can VeriflowAPI verify licenses in?",
             "Twelve states today: Texas, Florida, Illinois, Washington, Colorado, "
             "Connecticut, Alabama, New York, Pennsylvania, Ohio, California and Michigan. "
             "Federal NPPES identity and OIG exclusion screening runs in all 50 states on "
             "every check."),
            ("Is this primary-source verification?",
             "The data comes from the state boards themselves. The Illinois IDFPR lookup is "
             "recognised by the Joint Commission and NCQA as an approved primary source, and "
             "eLicense Ohio states the same. Every check returns a tamper-evident SHA-256 "
             "signed certificate recording which sources were consulted and when."),
            ("How current is the data?",
             "Mirrored states refresh daily, except California which follows its source's "
             "monthly publication. Live per-query states (Texas, New York, Pennsylvania, "
             "Ohio, Michigan) are checked at request time and cached for 24 hours. Every "
             "certificate records the as-of date, so staleness is visible rather than "
             "hidden."),
            ("What happens when a state board is down?",
             "We serve the most recent cached result and flag it with source_live: false and "
             "cached: true, so you can decide whether to accept it. If there is no cached "
             "result we say so rather than returning a guess."),
            ("Do you verify board certifications like ABPN, ABPP or BCBA?",
             "No. Those are issued by national certifying bodies rather than state boards. We "
             "verify the underlying state licence plus federal screening. Washington is the "
             "exception worth knowing: it licenses behavior analysts at state level, so a "
             "Washington BCBA's state credential is verifiable."),
        ])


# --- Use-case pages ----------------------------------------------------------

def telehealth_page() -> str:
    body = f"""  <section class="hero">
    <div class="badge">For telehealth platforms</div>
    <h1>Licensure follows the patient, not the provider</h1>
    <p class="sub">In telehealth the clinician must be licensed where the patient is located
    at the time of the encounter. That turns credentialing from a one-time check into a
    per-state, ongoing obligation.</p>
    <a class="cta cta-lg" href="{SIGNUP}">Start free &rarr; 100 verifications</a>
    <div class="free">No credit card required.</div>
  </section>

  <section>
    <h2>The problem is multiplication, not verification</h2>
    <p>A single physician on a national panel may hold licences in six states. Verifying them
    once at onboarding tells you very little: what matters is whether <em>this</em> clinician
    is currently licensed in <em>that</em> patient's state, today. A panel of 200 clinicians
    across 10 states is not 200 verifications, it is closer to 1,200 &mdash; and each licence
    lapses on its own schedule.</p>
    <p>Because state is a parameter rather than a property of the provider, the same person is
    checked independently per state:</p>
    <pre><span class="c"># Same clinician, two states, two independent licences</span>
POST /v1/verify  {{"first_name":"Jane","last_name":"Provider","state":<span class="s">"PA"</span>,"npi":"1234567890"}}
POST /v1/verify  {{"first_name":"Jane","last_name":"Provider","state":<span class="s">"OH"</span>,"npi":"1234567890"}}

<span class="c"># PA may return an active licence while OH returns expired. Both are true.</span></pre>
  </section>

  <section>
    <h2>Out-of-state telehealth registrations</h2>
    <p>Several states have created licence categories specifically for clinicians treating
    their residents from elsewhere. Florida is the clearest example: its MQA file carries
    dedicated out-of-state telehealth registration types alongside conventional licences, and
    they appear as their own licence type in a result. If your model is cross-state by design,
    those categories are often the ones that actually authorise the encounter.</p>
    <p>New York matters for a different reason. A New York licence does not expire &mdash; the
    triennial registration does &mdash; so the meaningful question is whether the clinician is
    currently <em>registered</em>, which is what we return.</p>
  </section>

  <section>
    <h2>Catch a lapse before the next appointment</h2>
    <p>A licence valid at onboarding can lapse mid-engagement, and nothing in your system will
    notice unless something is watching. Monitoring re-checks a provider on a schedule and
    posts a signed webhook when the status changes, an expiry approaches, a disciplinary flag
    appears, or an exclusion is added.</p>
    <div class="grid">
      <div class="card"><h3>license.expiry_approaching</h3><p>Fires ahead of the expiry date
      you configure, so a renewal can be chased before it affects scheduling.</p></div>
      <div class="card"><h3>license.status_changed</h3><p>Fires when the board's status moves,
      including to suspended or revoked.</p></div>
      <div class="card"><h3>license.oig_exclusion_added</h3><p>A federal exclusion appears
      after onboarding. A hard stop for any federally funded care.</p></div>
    </div>
  </section>

  <section>
    <h2>Coverage that matches a behavioural-health panel</h2>
    <p>Telehealth panels skew towards behavioural health, which is where state coverage
    usually thins out. Psychologists, LCSWs, LPC/LMHCs and LMFTs are verifiable in nine states
    today, and physicians in twelve. The <a href="/coverage.html#professions">role matrix</a>
    shows which state covers which licence, and uncovered states return an explicit
    <code>unsupported_state</code> rather than a guess &mdash; so you know precisely where
    human review is still required.</p>
  </section>
"""
    return page(
        path="for/telehealth.html",
        title="License Verification for Telehealth Platforms | VeriflowAPI",
        desc="Telehealth licensure follows the patient's state. Verify a clinician per state, "
             "catch lapses mid-engagement with signed webhooks, and cover behavioural-health "
             "roles across 12 states.",
        body=body,
        cta_h="Verify your panel, state by state",
        qas=[
            ("Which state should I verify for a telehealth encounter?",
             "Generally the state where the patient is located at the time of the encounter, "
             "since that is the jurisdiction whose licence authorises the care. State is a "
             "parameter on every request, so the same clinician can be verified independently "
             "in each state you operate in."),
            ("Do you cover out-of-state telehealth licence types?",
             "Yes, where the state publishes them. Florida's MQA file includes dedicated "
             "out-of-state telehealth registration categories for several professions, "
             "returned as their own licence type."),
            ("How do we find out a licence lapsed after onboarding?",
             "Set up monitoring for that provider. We re-check on a schedule and post a signed "
             "webhook on license.status_changed, license.expiry_approaching, license.expired, "
             "license.disciplinary_flag_added or license.oig_exclusion_added."),
            ("Does the sandbox behave like production?",
             "Yes. Test keys run against the same data and coverage as live keys, so an "
             "ordinary provider returns exactly what production would. Reserved test names "
             "force specific outcomes when you need to exercise error handling."),
        ])


def credentialing_page() -> str:
    body = f"""  <section class="hero">
    <div class="badge">For credentialing software</div>
    <h1>Primary-source verification, with the paperwork attached</h1>
    <p class="sub">Credentialing does not just need the right answer. It needs an auditable
    record of where that answer came from and when &mdash; one that still holds up in a survey
    two years later.</p>
    <a class="cta cta-lg" href="{SIGNUP}">Start free &rarr; 100 verifications</a>
    <div class="free">No credit card required.</div>
  </section>

  <section>
    <h2>The evidence, not just the status</h2>
    <p>Every verification produces a tamper-evident certificate: canonical JSON with a SHA-256
    hash and an HMAC signature, retained for seven years and retrievable as JSON or PDF. It
    records the provider details submitted, the sources consulted, the result read at that
    timestamp, and the signing key used. That is an audit-quality record of a federated
    lookup, which is what a surveyor actually asks to see.</p>
    <pre><span class="c"># Every verification returns an identifier and a signed hash</span>
{{
  <span class="k">"verification_id"</span>: <span class="s">"vrf_a1b2c3d4e5"</span>,
  <span class="k">"certificate_hash"</span>: <span class="s">"sha256_9f8e7d6c5b4a..."</span>,
  <span class="k">"sources_checked"</span>: [<span class="s">"NPPES"</span>, <span class="s">"OIG"</span>, <span class="s">"IL Division of Professional Regulation (primary source)"</span>],
  <span class="k">"checked_at"</span>: <span class="s">"2026-09-07T10:30:00Z"</span>
}}

<span class="c"># Retrieve the full certificate later, as JSON or PDF</span>
GET /v1/certificates/vrf_a1b2c3d4e5</pre>
    <p class="muted">To be precise about what a certificate is: it attests what the sources
    said at the time we read them. It is not an independent legal attestation that a provider
    is properly licensed, and we would rather state that plainly than let the distinction
    surface during an audit.</p>
  </section>

  <section>
    <h2>Sources your accreditors already accept</h2>
    <p>The Illinois IDFPR lookup is recognised by the Joint Commission and NCQA as an approved
    primary source, and eLicense Ohio states the same for its online status. Where a state's
    data is a mirror of the board's own published file, the certificate records that file's
    as-of date, so the age of the evidence is explicit rather than assumed.</p>
  </section>

  <section>
    <h2>Retiring the scraper fleet</h2>
    <p>Most credentialing platforms end up maintaining per-board integrations, and they break
    quietly rather than loudly. A board redesigns its portal; a bulk file silently stops
    updating; a state exposes a status field whose meaning is not what it appears.</p>
    <p>Two examples from states we run in production. Ohio's headline status is coarse &mdash;
    Active, Inactive, Closed &mdash; while the real detail sits in a sub-status such as Lapsed
    or Suspended, so a naive integration reports a lapsed credential as active. Pennsylvania
    returns every licence a person has ever held, frequently listing an expired graduate
    training permit ahead of the active MD, so a first-match integration reports a practising
    physician as expired. Those are the details that turn into a bad credentialing decision,
    and they are the work you stop maintaining.</p>
  </section>

  <section>
    <h2>Re-credentialing cycles</h2>
    <p>Re-verification is periodic by nature, and bulk verification accepts up to 100 providers
    per call for cycle work. Between cycles, monitoring posts a signed webhook when a status
    changes, so a suspension mid-cycle does not wait for the next review date. Each
    re-verification produces its own certificate, which is what builds the longitudinal file a
    surveyor expects.</p>
  </section>
"""
    return page(
        path="for/credentialing-software.html",
        title="Primary-Source License Verification API for Credentialing Software | VeriflowAPI",
        desc="Signed, audit-ready verification certificates retained seven years, sources "
             "accepted by the Joint Commission and NCQA, and one API in place of a fleet of "
             "state-board scrapers.",
        body=body,
        cta_h="Put verification evidence in your credentialing file",
        qas=[
            ("Is this accepted as primary-source verification?",
             "The Illinois IDFPR lookup is recognised by the Joint Commission and NCQA as an "
             "approved primary source, and eLicense Ohio states the same for its online "
             "status. Data comes from the state boards themselves, and each certificate "
             "records which sources were consulted and when."),
            ("What exactly is in the certificate?",
             "Canonical JSON with a SHA-256 hash and an HMAC signature: the provider details "
             "submitted, the sources consulted, the result read at that timestamp, and the "
             "signing key id. Retrievable as JSON or PDF, independently verifiable, retained "
             "for seven years."),
            ("Can we re-verify a whole panel at once?",
             "Yes. Bulk verification accepts up to 100 providers per call, which suits "
             "re-credentialing cycles. Between cycles, monitoring posts a signed webhook when "
             "a provider's status changes."),
            ("How do you avoid false OIG exclusions on common names?",
             "Around 90% of exclusion records carry no NPI, so name-only matching over-flags. "
             "A matching npi or dob confirms an exclusion and a different one rules that "
             "record out as a different person. Sending dob is the most effective way to clear "
             "a common-name collision."),
        ])


def staffing_page() -> str:
    body = f"""  <section class="hero">
    <div class="badge">For healthcare staffing</div>
    <h1>Screen fast at placement, keep watching through the assignment</h1>
    <p class="sub">Staffing runs on speed and volume: a candidate cleared today, placed
    tomorrow, working an assignment for thirteen weeks. Verification has to be quick at the
    front and continuous afterwards.</p>
    <a class="cta cta-lg" href="{SIGNUP}">Start free &rarr; 100 verifications</a>
    <div class="free">No credit card required.</div>
  </section>

  <section>
    <h2>Volume screening</h2>
    <p>Bulk verification takes up to 100 providers in a single call, which fits a candidate
    batch or a periodic sweep of an active roster. Mirrored states answer from our own copy of
    the board's file, so those lookups are immediate; live per-query states are checked against
    the board at request time and cached for 24 hours, so a repeat check inside a day does not
    wait on the state's portal twice.</p>
    <pre><span class="c"># Screen a candidate batch in one request</span>
POST /v1/verify/bulk

{{
  <span class="k">"providers"</span>: [
    {{<span class="k">"first_name"</span>: <span class="s">"Jane"</span>, <span class="k">"last_name"</span>: <span class="s">"Provider"</span>, <span class="k">"state"</span>: <span class="s">"FL"</span>, <span class="k">"npi"</span>: <span class="s">"1234567890"</span>}},
    {{<span class="k">"first_name"</span>: <span class="s">"Sam"</span>,  <span class="k">"last_name"</span>: <span class="s">"Clinician"</span>, <span class="k">"state"</span>: <span class="s">"OH"</span>, <span class="k">"dob"</span>: <span class="s">"1985-02-14"</span>}}
  ]
}}</pre>
  </section>

  <section>
    <h2>Exclusions are the disqualifier that carries penalties</h2>
    <p>Placing an excluded individual into a role paid by federal healthcare funding creates
    civil monetary penalty exposure for the facility, which is precisely the risk a staffing
    partner is hired to absorb. OIG exclusion screening runs on every check, nationwide, and
    returns the exclusion type and dates rather than a bare boolean.</p>
    <p>The failure mode to design around is the opposite one: a false exclusion on a common
    name, which pulls a perfectly employable candidate out of your pipeline. Because roughly
    90% of exclusion records carry no NPI, name-only matching over-flags. Send a
    <code>dob</code> (and an <code>npi</code> where you have it) and a same-name stranger is
    ruled out rather than costing you a placement.</p>
  </section>

  <section>
    <h2>The assignment outlasts the check</h2>
    <p>A thirteen-week assignment easily outlives the licence verified on day one. Monitoring
    re-checks placed clinicians on a schedule and posts a signed webhook the moment something
    moves &mdash; a status change, an approaching expiry, a new disciplinary flag, a newly
    added exclusion &mdash; so the facility hears it from you rather than the other way round.
    Deliveries retry on a 5m, 30m, 2h, 8h, 24h backoff and carry an HMAC signature you can
    verify.</p>
  </section>

  <section>
    <h2>Multi-state travellers</h2>
    <p>Travel clinicians are licensed wherever they have worked, and each licence lapses on its
    own schedule. Verify per state for the assignment in question, and know what a result means
    in that state: Alabama's roster reflects currently active licences, New York reports
    registration rather than expiry, and California's monthly file carries status and expiry
    but no disciplinary history. The <a href="/coverage.html">coverage page</a> sets out each
    source and its limits, so you can tell a client exactly what a clear result covers.</p>
  </section>
"""
    return page(
        path="for/healthcare-staffing.html",
        title="License and Exclusion Screening API for Healthcare Staffing | VeriflowAPI",
        desc="Screen candidates in bulk, avoid false OIG exclusions on common names, and get "
             "signed webhooks when a placed clinician's licence changes mid-assignment.",
        body=body,
        cta_h="Screen candidates and monitor placements",
        qas=[
            ("How many providers can we screen in one call?",
             "Bulk verification accepts up to 100 providers per request, which suits a "
             "candidate batch or a periodic sweep of an active roster."),
            ("How do we avoid losing a good candidate to a false OIG hit?",
             "Send a date of birth, and an NPI where you have one. Roughly 90% of exclusion "
             "records carry no NPI, so a name-only match over-flags common names. A matching "
             "npi or dob confirms an exclusion; a different one rules that record out as a "
             "different person."),
            ("What happens if a licence lapses during an assignment?",
             "Monitoring re-checks placed clinicians on a schedule and posts a signed webhook "
             "on license.status_changed, license.expiry_approaching, license.expired, "
             "license.disciplinary_flag_added or license.oig_exclusion_added. Failed "
             "deliveries retry on a 5m to 24h backoff."),
            ("Can we verify travel clinicians in several states?",
             "Yes. State is a parameter on every request, so the same clinician is verified "
             "independently in each state. The coverage page sets out what each state's source "
             "does and does not include."),
        ])


def write_sitemap(urls: list[str]) -> None:
    core = ["/", "/status.html", "/terms.html", "/privacy.html"]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in core + sorted(urls):
        lines.append(f"  <url><loc>{SITE}{u}</loc></url>")
    lines.append("</urlset>")
    write("sitemap.xml", "\n".join(lines) + "\n")


def main() -> None:
    write("verify/seo.css", CSS)
    urls = [coverage_page(), telehealth_page(), credentialing_page(), staffing_page()]

    for path, target in REDIRECTS.items():
        html = STUB.replace("__TARGET_ABS__", SITE + target).replace("__TARGET__", target)
        write(path, html)

    write_sitemap(urls)
    print(f"{len(urls)} content pages + seo.css; {len(REDIRECTS)} redirect stubs")
    for u in urls:
        print("   ", u)


if __name__ == "__main__":
    main()
