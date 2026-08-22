#!/usr/bin/env python3
"""Generate SEO landing pages (state / profession / use-case) for veriflowapi.com.

Static output only — writes self-contained HTML under verify/ and for/, plus a shared
seo.css, and refreshes sitemap.xml. Re-run any time coverage changes. Content is kept
consistent with docs/data-sources.mdx and the coverage communicated to customers.

    python build_seo_pages.py
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://veriflowapi.com"
SIGNUP = "https://app.veriflowapi.com/signup"

# --- Data -------------------------------------------------------------------

# Live states (slug, display, board, one-line coverage fact).
STATES = [
    ("texas", "Texas", "Texas Medical Board",
     "physicians, physician assistants, and more, via a live per-query board search"),
    ("florida", "Florida", "Florida Department of Health (MQA)",
     "1.5M+ licensees across 180+ professions from the official MQA data portal"),
    ("illinois", "Illinois", "Illinois IDFPR",
     "a Joint Commission and NCQA approved primary source, refreshed daily"),
    ("washington", "Washington", "Washington Department of Health",
     "physicians, nurses, and behavioral and allied health credentials"),
    ("colorado", "Colorado", "Colorado DORA",
     "health and occupational licenses from the state open-data mirror"),
    ("connecticut", "Connecticut", "Connecticut DCP",
     "state licenses and credentials, refreshed daily"),
    ("alabama", "Alabama", "Alabama Board of Medical Examiners",
     "MD, DO, and CRNP/CNM licenses, primary-source verified"),
    ("newyork", "New York", "New York Office of the Professions",
     "physicians, psychologists, social workers, counselors, PT, OT, and SLP"),
]
STATE_ABBR = {"texas": "TX", "florida": "FL", "illinois": "IL", "washington": "WA",
              "colorado": "CO", "connecticut": "CT", "alabama": "AL", "newyork": "NY"}

# Professions (slug, display, license, covered-state abbreviations).
ALL_CLINICAL = ["FL", "WA", "IL", "CO", "CT", "NY"]
PROFESSIONS = [
    ("physician", "Physician", "State Medical MD/DO license",
     ["TX", "FL", "IL", "WA", "CO", "CT", "AL", "NY"]),
    ("psychologist", "Psychologist", "Licensed Psychologist license", ALL_CLINICAL),
    ("clinical-social-worker", "Licensed Clinical Social Worker (LCSW)",
     "clinical social work license", ALL_CLINICAL),
    ("professional-counselor", "Licensed Professional Counselor (LPC / LMHC)",
     "professional / mental-health counselor license", ALL_CLINICAL),
    ("marriage-family-therapist", "Marriage and Family Therapist (LMFT)",
     "LMFT license", ALL_CLINICAL),
    ("physical-therapist", "Physical Therapist", "PT license", ALL_CLINICAL),
    ("occupational-therapist", "Occupational Therapist", "OT license", ALL_CLINICAL),
    ("speech-language-pathologist", "Speech-Language Pathologist", "SLP license", ALL_CLINICAL),
]

# Use cases (slug, display, audience noun, pain line).
USE_CASES = [
    ("telehealth", "Telehealth Platforms", "telehealth platform",
     "verify every provider's license and federal standing before they see a patient"),
    ("credentialing-software", "Credentialing Software", "credentialing platform",
     "replace brittle per-board scrapers with one primary-source verification call"),
    ("healthcare-staffing", "Healthcare Staffing", "staffing platform",
     "screen clinicians across states at scale, with a signed record on every check"),
    ("provider-onboarding", "Provider Onboarding", "onboarding flow",
     "drop one API call into onboarding to confirm license, NPI, and exclusion status"),
    ("marketplaces", "Healthcare Marketplaces", "marketplace",
     "verify every provider who joins, and keep watching for status changes"),
]

# --- Shared CSS -------------------------------------------------------------

CSS = """/* Shared styles for VeriflowAPI SEO landing pages. */
:root{--ink:#0f1117;--ink-muted:#6b7080;--surface:#fafaf8;--surface-2:#f4f3ef;
--accent:#1a4fff;--accent-light:#e8eeff;--accent-dark:#1238cc;--success:#0ea561;
--border:#e2e0d8;--code-bg:#0f1117;}
*{box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{margin:0;font-family:'DM Sans',system-ui,sans-serif;color:var(--ink);
background:var(--surface);line-height:1.6;-webkit-font-smoothing:antialiased;}
a{color:var(--accent);text-decoration:none;}
a:hover{text-decoration:underline;}
.wrap{max-width:920px;margin:0 auto;padding:0 24px;}
header.nav{border-bottom:1px solid var(--border);background:rgba(250,250,248,.9);
backdrop-filter:blur(8px);position:sticky;top:0;z-index:10;}
.nav .wrap{display:flex;align-items:center;justify-content:space-between;height:62px;}
.logo{font-family:'DM Serif Display',serif;font-size:1.35rem;color:var(--ink);}
.logo span{color:var(--accent);}
.cta{background:var(--accent);color:#fff;padding:.6rem 1.15rem;border-radius:7px;
font-weight:600;font-size:.9rem;display:inline-block;}
.cta:hover{background:var(--accent-dark);text-decoration:none;}
.cta-lg{padding:.85rem 1.6rem;font-size:1rem;}
h1{font-family:'DM Serif Display',serif;font-size:2.6rem;line-height:1.1;margin:.2em 0;}
h2{font-family:'DM Serif Display',serif;font-size:1.7rem;margin:1.6em 0 .5em;}
.badge{display:inline-block;background:var(--accent-light);color:var(--accent-dark);
font-size:.78rem;font-weight:600;padding:.3rem .7rem;border-radius:100px;margin-bottom:1rem;}
.hero{padding:64px 0 40px;}
.hero p.sub{font-size:1.18rem;color:var(--ink-muted);max-width:640px;}
.hero .cta-lg{margin-top:1.4rem;}
.free{font-size:.85rem;color:var(--ink-muted);margin-top:.7rem;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin:1em 0;}
.card{background:#fff;border:1px solid var(--border);border-radius:12px;padding:20px;}
.card h3{margin:.1em 0 .35em;font-size:1.05rem;}
.card p{margin:0;color:var(--ink-muted);font-size:.95rem;}
pre{background:var(--code-bg);color:#e6e9f2;border-radius:12px;padding:20px;overflow-x:auto;
font-family:'DM Mono',ui-monospace,monospace;font-size:.82rem;line-height:1.6;}
pre .k{color:#8ab4ff;}pre .s{color:#8ce0a8;}pre .b{color:#ffb454;}pre .c{color:#6b7080;}
.states{display:flex;flex-wrap:wrap;gap:8px;margin:.6em 0;}
.pill{background:var(--surface-2);border:1px solid var(--border);border-radius:100px;
padding:.3rem .8rem;font-size:.85rem;font-weight:500;}
.faq{margin:.8em 0;}
.faq details{border-bottom:1px solid var(--border);padding:.9em 0;}
.faq summary{font-weight:600;cursor:pointer;}
.faq p{color:var(--ink-muted);margin:.6em 0 0;}
.cta-band{background:var(--accent-light);border-radius:16px;padding:40px;text-align:center;margin:48px 0;}
.cta-band h2{margin-top:0;}
footer{border-top:1px solid var(--border);padding:32px 0;color:var(--ink-muted);font-size:.85rem;}
footer a{color:var(--ink-muted);}
.muted{color:var(--ink-muted);}
@media(max-width:640px){h1{font-size:2rem;}.hero{padding:40px 0 28px;}}
"""

# --- Template ---------------------------------------------------------------

PAGE = """<!doctype html>
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
<link rel="stylesheet" href="__CSS__"/>
<script type="application/ld+json">__JSONLD__</script>
</head>
<body>
<header class="nav"><div class="wrap">
  <a class="logo" href="/">Veri<span>flow</span>API</a>
  <a class="cta" href="__SIGNUP__">Start Free &rarr;</a>
</div></header>

<main class="wrap">
  <section class="hero">
    <div class="badge">__BADGE__</div>
    <h1>__H1__</h1>
    <p class="sub">__SUB__</p>
    <a class="cta cta-lg" href="__SIGNUP__">Start free &rarr; 100 verifications</a>
    <div class="free">No credit card required. One API call returns license status, NPI identity, and OIG exclusion screening.</div>
  </section>

  <section>
    <div class="grid">
      <div class="card"><h3>One call, normalized</h3><p>Skip per-board formats and portals. Submit a provider, get a single clean JSON response.</p></div>
      <div class="card"><h3>Federal screening built in</h3><p>NPPES identity and OIG exclusion checks run nationwide on every verification.</p></div>
      <div class="card"><h3>Signed certificate</h3><p>Every check returns a tamper-evident, SHA-256 signed certificate, retained seven years.</p></div>
    </div>
  </section>

  __BODY__

  <section>
    <h2>Example request</h2>
    <pre>__CODE__</pre>
  </section>

  <section class="faq">
    <h2>FAQ</h2>
    __FAQ__
  </section>

  <div class="cta-band">
    <h2>__CTA_H__</h2>
    <p class="muted" style="max-width:560px;margin:0 auto 1.2rem;">Start with 100 free verifications. No credit card. Read the <a href="https://docs.veriflowapi.com/introduction">docs</a> or explore <a href="https://docs.veriflowapi.com/data-sources">coverage</a>.</p>
    <a class="cta cta-lg" href="__SIGNUP__">Create your account &rarr;</a>
  </div>
</main>

<footer><div class="wrap">
  &copy; 2026 SecureHealth AI LLC d/b/a Veriflow &middot;
  <a href="/">Home</a> &middot;
  <a href="https://docs.veriflowapi.com/introduction">Docs</a> &middot;
  <a href="/terms.html">Terms</a> &middot;
  <a href="/privacy.html">Privacy</a>
</div></footer>
</body>
</html>
"""


def code_block(state_full: str, abbr: str, board: str) -> str:
    return (
        '<span class="c"># One call verifies license + NPI + OIG</span>\n'
        'POST https://api.veriflowapi.com/v1/verify\n\n'
        '{\n'
        '  <span class="k">"first_name"</span>: <span class="s">"Jane"</span>,\n'
        '  <span class="k">"last_name"</span>: <span class="s">"Provider"</span>,\n'
        f'  <span class="k">"state"</span>: <span class="s">"{abbr}"</span>\n'
        '}\n\n'
        '<span class="c"># Response</span>\n'
        '{\n'
        '  <span class="k">"verified"</span>: <span class="b">true</span>,\n'
        '  <span class="k">"status"</span>: <span class="s">"active"</span>,\n'
        f'  <span class="k">"state"</span>: <span class="s">"{state_full}"</span>,\n'
        '  <span class="k">"license_number"</span>: <span class="s">"..."</span>,\n'
        '  <span class="k">"expiry_date"</span>: <span class="s">"2027-05-31"</span>,\n'
        '  <span class="k">"oig_excluded"</span>: <span class="b">false</span>,\n'
        f'  <span class="k">"sources_checked"</span>: [<span class="s">"NPPES"</span>, <span class="s">"OIG"</span>, <span class="s">"{board}"</span>],\n'
        '  <span class="k">"certificate_hash"</span>: <span class="s">"sha256_..."</span>\n'
        '}'
    )


def faq_html(qas: list[tuple[str, str]]) -> str:
    return "\n    ".join(
        f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in qas)


def jsonld(title: str, desc: str, canon: str, qas: list[tuple[str, str]]) -> str:
    import json
    faqs = [{"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qas]
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "name": title, "description": desc, "url": canon},
            {"@type": "FAQPage", "mainEntity": faqs},
        ],
    }
    return json.dumps(data)


def render(*, path, title, desc, badge, h1, sub, body, code, cta_h, qas):
    canon = f"{SITE}/{path}"
    html = PAGE
    repl = {
        "__TITLE__": title, "__DESC__": desc, "__CANON__": canon,
        "__CSS__": "/verify/seo.css", "__SIGNUP__": SIGNUP, "__BADGE__": badge,
        "__H1__": h1, "__SUB__": sub, "__BODY__": body, "__CODE__": code,
        "__CTA_H__": cta_h, "__FAQ__": faq_html(qas),
        "__JSONLD__": jsonld(title, desc, canon, qas),
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    out = os.path.join(HERE, path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return f"/{path}"


def main() -> None:
    urls: list[str] = []
    os.makedirs(os.path.join(HERE, "verify"), exist_ok=True)
    with open(os.path.join(HERE, "verify", "seo.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    # State pages
    for slug, name, board, fact in STATES:
        abbr = STATE_ABBR[slug]
        body = (
            f"<section><h2>Live {name} license data</h2>"
            f"<p>VeriflowAPI verifies {name} professional licenses against the {board}, returning "
            f"{fact}. Every check also runs nationwide federal screening, so you get license status, "
            f"NPI identity, and OIG exclusion in a single response.</p></section>"
        )
        qas = [
            (f"Does VeriflowAPI verify {name} medical licenses?",
             f"Yes. {name} is live today. We verify license status and expiry against the {board}, "
             f"plus nationwide NPPES and OIG screening on every check."),
            ("How current is the data?",
             "Mirrored state data refreshes daily; live-scrape states are checked per query with a "
             "24-hour cache. Each certificate records exactly when the source was read."),
            ("What does a failed check look like?",
             "The response is explicit: status, oig_excluded, and disciplinary flags are separate "
             "fields, and unsupported states return an unsupported_state status rather than fabricated data."),
        ]
        urls.append(render(
            path=f"verify/{slug}-license-verification.html",
            title=f"{name} Medical License Verification API | VeriflowAPI",
            desc=f"Verify {name} professional and medical licenses in one API call. Live {board} "
                 f"data plus NPPES + OIG screening. Start free with 100 verifications.",
            badge=f"{name} &middot; Live today",
            h1=f"{name} License Verification API",
            sub=f"Verify {name} providers in one call against the {board}, with federal NPI and "
                f"OIG screening built in.",
            body=body,
            code=code_block(name, abbr, board),
            cta_h=f"Verify {name} providers in one call",
            qas=qas))

    # Profession pages
    for slug, name, lic, states in PROFESSIONS:
        pills = "".join(f'<span class="pill">{s}</span>' for s in states)
        body = (
            f"<section><h2>Verify {name} licenses</h2>"
            f"<p>A {name.split('(')[0].strip().lower()} holds a {lic}, which VeriflowAPI verifies "
            f"directly against the issuing state board. Coverage today:</p>"
            f'<div class="states">{pills}</div>'
            f"<p class='muted'>Federal NPPES identity and OIG exclusion screening run on every "
            f"check in all 50 states. Other states return an honest unsupported_state response.</p></section>"
        )
        qas = [
            (f"Which states can I verify {name} licenses in?",
             "Live today in " + ", ".join(states) + ". Federal NPI and OIG screening is nationwide."),
            ("Is the license the same as a board certification?",
             "We verify the underlying state license (the legal authorization to practice) plus federal "
             "screening. National sub-certifications from private boards are separate registries."),
        ]
        urls.append(render(
            path=f"verify/{slug}-license-verification.html",
            title=f"{name} License Verification API | VeriflowAPI",
            desc=f"Verify {name} licenses in one API call across {len(states)} states, with NPPES + "
                 f"OIG screening. Start free with 100 verifications.",
            badge="Profession coverage",
            h1=f"{name} License Verification",
            sub=f"One API call verifies a {name.split('(')[0].strip().lower()}'s state license, NPI "
                f"identity, and federal exclusion status.",
            body=body,
            code=code_block("Florida", "FL", "FL Department of Health"),
            cta_h=f"Verify {name.split('(')[0].strip()} licenses in one call",
            qas=qas))

    # Use-case pages
    for slug, name, audience, pain in USE_CASES:
        body = (
            f"<section><h2>Built for {name.lower()}</h2>"
            f"<p>If you run a {audience}, VeriflowAPI lets you {pain}. One endpoint replaces the "
            f"per-state board integrations, portals, and formats you would otherwise maintain, and "
            f"returns a signed certificate you can keep for audit.</p></section>"
            f"<section><div class='grid'>"
            f"<div class='card'><h3>Verify at onboarding</h3><p>Confirm license, NPI, and OIG status "
            f"before a provider goes live.</p></div>"
            f"<div class='card'><h3>Monitor continuously</h3><p>Webhooks alert you when a license "
            f"lapses, is disciplined, or an exclusion is added.</p></div>"
            f"<div class='card'><h3>Audit-ready</h3><p>Every check produces a tamper-evident signed "
            f"certificate, retained seven years.</p></div>"
            f"</div></section>"
        )
        qas = [
            ("How fast can we integrate?",
             "One REST endpoint and a bearer token. Most teams run their first live check the same "
             "day, with 100 free verifications to test."),
            ("Which states and roles are covered?",
             "Deep license data for eight states today (TX, FL, IL, WA, CO, CT, AL, NY) across "
             "physician and behavioral-health roles, plus nationwide federal screening. See the "
             "coverage page for the current list."),
        ]
        urls.append(render(
            path=f"for/{slug}.html",
            title=f"License Verification API for {name} | VeriflowAPI",
            desc=f"VeriflowAPI helps {name.lower()} {pain}. One API call, signed certificates, 100 "
                 f"free verifications to start.",
            badge=f"For {name.lower()}",
            h1=f"License Verification for {name}",
            sub=f"Give your {audience} one API call to {pain}.",
            body=body,
            code=code_block("Texas", "TX", "TX Medical Board"),
            cta_h=f"Add provider verification to your {audience}",
            qas=qas))

    write_sitemap(urls)
    print(f"Generated {len(urls)} pages + seo.css")
    for u in urls:
        print("  ", u)


def write_sitemap(new_urls: list[str]) -> None:
    """Rebuild sitemap.xml: the core pages plus every generated page."""
    core = ["/", "/terms.html", "/privacy.html"]
    all_urls = core + sorted(new_urls)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in all_urls:
        lines.append(f"  <url><loc>{SITE}{u}</loc></url>")
    lines.append("</urlset>")
    with open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
