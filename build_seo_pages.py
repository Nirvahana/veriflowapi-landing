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
    research/state-license-data-sources.html
                                      reference page: what every state publishes (not what we verify)
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
    dict(slug="delaware", abbr="DE", name="Delaware",
         board="Division of Professional Regulation (DPR)", method="Daily mirror",
         refresh="Refreshed daily", records="63,000 licensees",
         discipline="Yes",
         detail="Delaware publishes its whole consolidated licence database as open data, "
                "refreshed every morning, so the state is mirrored daily. It covers medical "
                "practice, psychology, social work, mental health counselling, physical "
                "therapy, occupational therapy and speech and hearing in a single file, with "
                "a separate register of board disciplinary actions that we join on the "
                "licence number.",
         caveat="The licence file carries its own disciplinary column, but it reads “no” "
                "on every row in the state, revoked licences included, so we ignore it and use "
                "the published disciplinary register instead. That matters: several hundred "
                "Delaware licensees are currently active AND carry a board action, which the "
                "file alone would have reported as clean. Delaware publishes no NPI."),
    dict(slug="newjersey", abbr="NJ", name="New Jersey",
         board="Division of Consumer Affairs (DCA)", method="Daily mirror",
         refresh="Refreshed daily", records="294,000 licensees",
         discipline="Partial",
         detail="New Jersey runs a single licensing system across its boards and publishes a "
                "roster download rather than requiring a per-name lookup, so we mirror it "
                "daily. Eight profession rosters cover physicians and physician assistants, "
                "psychologists, social workers, professional counselors and marriage and "
                "family therapists, physical therapists, occupational therapists and "
                "speech-language pathologists and audiologists.",
         caveat="The New Jersey roster carries licence status and expiry but no disciplinary "
                "history column. We report a sanction where the state encodes one in the "
                "licence status itself, such as a suspension or a voluntary surrender, but a "
                "board action against a licence that is otherwise current will not appear. "
                "Roughly one row in seven is an application that never became a licence, "
                "carrying no licence number at all; we drop those rather than count them as "
                "licensees."),
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
    dict(slug="massachusetts", abbr="MA", name="Massachusetts",
         board="Board of Registration in Medicine (BORIM)", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="Physicians are verified live against the Board of Registration in Medicine's public profile service at the moment you ask. It returns the licence number, status, issue and expiry dates, the NPI, four categories of disciplinary action (in-state board, out-of-state board, healthcare facility, criminal) and malpractice history.",
         caveat="Massachusetts is the first live state where we can match on NPI, so a request that carries one returns high confidence. The disciplinary flag is raised by any board or facility action, a criminal conviction, or a malpractice record; the categories are kept separately in the raw payload so you can tell them apart. Physicians only: the Department of Public Health boards that license the other professions were not reachable from our infrastructure and are not covered."),
    dict(slug="rhodeisland", abbr="RI", name="Rhode Island",
         board="Department of Health (RIDOH)", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Partial",
         detail="Rhode Island is verified live against the Department of Health's licence lookup at the moment you ask. It covers physicians, psychologists, social workers, mental health counsellors, marriage and family therapists, physical and occupational therapists and speech-language pathologists, returning licence number, type, status, issue and expiry dates.",
         caveat="The lookup's detail page carries no per-licensee disciplinary record, only a link to the board's published list, so the disciplinary flag is derived from the licence status alone: probation, restriction, suspension, surrender or revocation. A board action against a licence that is otherwise active will not appear. No NPI."),
    dict(slug="dc", abbr="DC", name="District of Columbia",
         board="DC Health, Health Regulation and Licensing (HRLA)", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="The District is verified live against DC Health's licence verification at the moment you ask, across all eight professions. Each result carries licence number, type, status, issue and expiry dates, and links to any public board orders.",
         caveat="DC's search matches both names loosely, so we require an exact surname and confirm the given name before reporting anyone; a nickname resolves only when it is contained in the registered name. The disciplinary flag is raised by a public board order on the record or by a sanction status, and the order documents are kept in the raw payload. No NPI."),
    dict(slug="kansas", abbr="KS", name="Kansas",
         board="Board of Healing Arts (KSBHA) and Behavioral Sciences Regulatory Board (BSRB)", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="Kansas is verified live against two boards at the moment you ask: the Board of Healing Arts for physicians, physical and occupational therapists, and the Behavioral Sciences Regulatory Board for psychologists, social workers, professional counsellors and marriage and family therapists. Both publish board actions, which raise the disciplinary flag.",
         caveat="Kansas physician profiles publish a cancellation date rather than an expiry date, and we surface that as the expiry. Speech-language pathology is licensed by a different department and is not covered. Names are matched by prefix at the source, so we require an exact surname. No NPI."),
    dict(slug="vermont", abbr="VT", name="Vermont",
         board="Board of Medical Practice (BMP)", method="Daily mirror",
         refresh="Refreshed daily", records="25,000 licensees",
         discipline="Yes",
         detail="We mirror the Board of Medical Practice's public roster every day: physicians, physician assistants, podiatrists and anesthesiologist assistants. Each record carries licence number, type, status, issue and expiry dates.",
         caveat="Vermont's roster uses 35 distinct status strings, and several that read as active are not: a licence marked inoperable has no practice agreement behind it, so we report it as inactive. Sanctions such as reprimand, conditions and surrender are encoded in the status, and we raise the disciplinary flag from those; the roster's own notes column is not a discipline signal and is ignored. Vermont's other professions are licensed by a separate office that is not in this roster."),
    dict(slug="wyoming", abbr="WY", name="Wyoming",
         board="Professional Licensing Boards (A&I)", method="Daily mirror",
         refresh="Refreshed daily", records="12,000 licensees",
         discipline="Yes",
         detail="We mirror the public rosters of three Wyoming boards every day: Mental Health Professions (counsellors, social workers, marriage and family therapists, addiction professionals), Psychology, and Speech-Language Pathology and Audiology. Each record carries licence number, type, status, issue and expiry dates and a discipline indicator.",
         caveat="Physicians are not covered: the Board of Medicine's lookup sits behind a web application firewall and we do not work around it. The rosters are maintained by hand, so we validate their layout on every run and keep the previous day's data if a sheet changes shape. Speech-language pathology's expired roster has no discipline column. No NPI."),
    dict(slug="idaho", abbr="ID", name="Idaho",
         board="Division of Occupational and Professional Licenses (DOPL)", method="Daily mirror",
         refresh="Refreshed daily", records="55,000 licensees",
         discipline="Yes",
         detail="We mirror Idaho's consolidated licensing division every day across all eight professions. Each record carries licence number, type, status, issue and expiry dates and the division's own discipline indicator.",
         caveat="Idaho publishes a discipline indicator per licence, which raises the flag for several hundred licensees who are currently active; suspension and revocation raise it too. Lapsed licences are reported as expired. Residents, interns and provisional licences are labelled as such. No NPI."),
    dict(slug="mississippi", abbr="MS", name="Mississippi",
         board="five professional licensing boards", method="Weekly mirror",
         refresh="Refreshed weekly", records="32,000 licensees",
         discipline="Yes",
         detail="We mirror five Mississippi boards: professional counselling, physical therapy, social work and marriage and family therapy, and the Department of Health boards covering speech-language pathology, audiology and occupational therapy. Each record carries licence number, type, status, expiry and a discipline indicator.",
         caveat="Physicians are not covered: the medical board's only free search is CAPTCHA-gated and its paid channels forbid resale, so we leave it out rather than misrepresent coverage. The psychology board is also excluded because it publishes no licence status at all, and a record without a status cannot answer the question customers ask. Mississippi refreshes weekly rather than daily because these boards offer no bulk download and each refresh is thousands of individual requests. No NPI."),
    dict(slug="maryland", abbr="MD", name="Maryland",
         board="Board of Physicians (MBP)", method="Monthly mirror",
         refresh="Refreshed on the 1st of each month", records="65,000 licensees",
         discipline="Yes",
         detail="We mirror the Board of Physicians' monthly public rosters: physicians, allied health including physician assistants, and the inactive and emeritus lists. Each record carries licence number, status, expiry and a discipline indicator.",
         caveat="The physician roster lists current licensees only, so a physician whose licence has expired, been suspended or revoked is simply absent from it. Absence therefore returns not_found, which is not the same as never licensed; treat a Maryland not_found as something to check by hand. Probation is reported as active with the disciplinary flag raised. Because the source is monthly, every certificate records the as-of date. Physicians and allied health only; the behavioural-health boards are separate and not yet covered. No NPI."),
    dict(slug="newmexico", abbr="NM", name="New Mexico",
         board="Regulation and Licensing Dept. and the Medical Board", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="New Mexico is verified live at the moment you ask, across all eight professions. The Medical Board covers physicians; the Regulation and Licensing Department covers psychology, social work, counselling, marriage and family therapy, physical and occupational therapy and speech-language pathology.",
         caveat="Both boards publish their own disciplinary records, board orders and settlement agreements with case numbers, which we return. One mapping worth knowing: New Mexico uses revocation and suspension wording for an ordinary administrative lapse at the end of a term. We report those as expired rather than as sanctions, because treating them as discipline would misrepresent several hundred licensees. No NPI."),
    dict(slug="louisiana", abbr="LA", name="Louisiana",
         board="Board of Medical Examiners and Board of Examiners of Psychologists", method="Monthly mirror + live",
         refresh="Physicians monthly; psychologists checked live", records="50,000 physicians",
         discipline="Partial",
         detail="Louisiana covers two professions from two sources. Physicians come from the medical board's monthly published roster, about 50,000 licensees. Psychologists are verified live at the moment you ask, and that source publishes disciplinary action and board order flags.",
         caveat="The physician roster lists active licensees only, so a physician whose licence has lapsed, been suspended or revoked is absent from it rather than listed with that status. A Louisiana physician not_found is therefore not evidence that someone was never licensed. The roster carries no disciplinary column; only the psychologist source does. Louisiana's other boards do not publish a usable lookup, so the remaining six professions are not covered. No NPI."),
    dict(slug="iowa", abbr="IA", name="Iowa",
         board="Board of Medicine, Professional Licensure and the dental boards", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="Iowa is verified live across three state portals covering more than twenty boards: the Board of Medicine for physicians, the professional licensure boards for psychology, social work, behavioural science, physical and occupational therapy and speech-language pathology, and the dental boards.",
         caveat="Nursing, pharmacy and emergency medical services are licensed on separate systems we do not read, so an Iowa result covers the professions listed here and no others. Two things worth knowing: Iowa records a relinquished licence as the ordinary way a physician licence ends, which we do not treat as a sanction, and the Board of Medicine caps a name search, so we narrow by given name and status when that happens. No NPI."),
    dict(slug="arkansas", abbr="AR", name="Arkansas",
         board="State Medical Board, Psychology Board and the Speech-Language Pathology Board", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Partial",
         detail="Arkansas is verified live across three boards: the State Medical Board for physicians and occupational therapists, the Psychology Board, and the Speech-Language Pathology and Audiology Board.",
         caveat="Social work and physical therapy are not covered: those lookups are behind a blocked host and an image challenge, and we do not work around either. Counselling and marriage and family therapy are deliberately excluded for a different reason. That board's register parses cleanly but has not been updated since 2023, so publishing it would report long-expired licences as active. The medical and psychology boards publish disciplinary signals; the speech board's own discipline column reads clear even on revoked licensees, so we report no signal there rather than a false clean bill. No NPI."),
    dict(slug="kentucky", abbr="KY", name="Kentucky",
         board="Board of Medical Licensure and the Occupations and Professions boards", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="Kentucky is verified live across two systems covering six of our eight professions: the Board of Medical Licensure for physicians, and the state's professions portal for psychology, counselling, marriage and family therapy, occupational therapy and speech-language pathology. Both publish disciplinary signals.",
         caveat="Social work and physical therapy are not covered: both searches require a challenge we do not attempt. The physician application holds current credentials only, so a lapsed Kentucky physician is absent rather than returned as expired, and a physician not_found there is not evidence of never being licensed. Kentucky also marks some licensees active but not practising, or not eligible to practise, and we report those as inactive, because the board is saying the holder may not practise. No NPI."),
    dict(slug="westvirginia", abbr="WV", name="West Virginia",
         board="the social work, psychology, counselling and occupational therapy boards", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Yes",
         detail="West Virginia is verified live across four boards covering five professions: social work, psychology, professional counselling and marriage and family therapy, and occupational therapy. All four publish a disciplinary signal.",
         caveat="Physicians are not covered, and not because of us: both West Virginia medical board lookups resolve to an address that answers on no port from any resolver we tried, so they are unavailable to everyone. Physical therapy and speech-language pathology are behind a firewall and a challenge respectively. Where a board publishes no disciplinary signal we say so rather than implying a clean record, and licences marked active but non-practising are reported as inactive. No NPI."),
    dict(slug="oklahoma", abbr="OK", name="Oklahoma",
         board="Board of Examiners of Psychologists and the Speech-Language Pathology Board", method="Live per-query",
         refresh="Checked live, cached 24 hours", records="Live lookup",
         discipline="Partial",
         detail="Oklahoma covers two professions, verified live: psychologists, and speech-language pathologists and audiologists. This is a deliberately narrow entry and should be read as exactly that.",
         caveat="Physicians, physical therapy and occupational therapy all sit with the state medical board, whose published policy asks that its search not be harvested. We respect that and do not query it at all, so those professions are not covered and will not be. Counselling, marriage and family therapy and social work are behind a firewall. The psychology board publishes real case references, which we return; the speech board publishes no disciplinary signal at all and sanctioned licensees drop off its register, so we declare no signal rather than a clean record. The psychology board publishes no expiry date. No NPI."),
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

ALL_CLINICAL = ["FL", "WA", "IL", "CO", "CT", "NY", "PA", "OH", "CA", "MI", "NJ", "DE", "RI", "DC", "ID", "NM", "IA"]
NO_CA = [s for s in ALL_CLINICAL if s != "CA"]
ROLES = [
    ("Physician (MD / DO)", "State medical or osteopathic licence",
     ["TX", "FL", "IL", "WA", "CO", "CT", "AL", "NY", "PA", "OH", "CA", "MI", "NJ",
      "DE", "MA", "RI", "DC", "KS", "VT", "ID", "MD", "NM", "LA", "IA", "AR", "KY"]),
    ("Psychologist / Neuropsychologist", "Licensed Psychologist", ALL_CLINICAL + ["KS", "WY", "LA", "AR", "KY", "WV", "OK"]),
    ("Licensed Clinical Social Worker", "LCSW", ALL_CLINICAL + ["KS", "WY", "MS", "WV"]),
    ("Professional / Mental Health Counselor", "LPC, LPCC or LMHC", ALL_CLINICAL + ["KS", "WY", "MS", "KY", "WV"]),
    ("Marriage and Family Therapist", "LMFT", ALL_CLINICAL + ["KS", "WY", "MS", "KY", "WV"]),
    ("Physical Therapist", "PT", ALL_CLINICAL + ["KS", "MS"]),
    ("Occupational Therapist", "OT", ALL_CLINICAL + ["KS", "MS", "AR", "KY", "WV"]),
    ("Speech-Language Pathologist", "SLP", NO_CA + ["WY", "MS", "AR", "KY", "OK"]),
]
ALL_ABBR = ["TX", "FL", "IL", "WA", "CO", "CT", "AL", "NY", "PA", "OH", "CA", "MI", "NJ",
            "DE", "MA", "RI", "DC", "KS", "VT", "WY", "ID", "MS", "MD", "NM", "LA", "IA", "AR", "KY", "WV", "OK"]

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
/* Research pages: wide reference tables scroll inside their own container. */
.tablewrap{overflow-x:auto;margin:1em 0;}
.tablewrap table{min-width:820px;font-size:.86rem;}
.tablewrap td{vertical-align:top;}
.tablewrap.wide{width:min(1360px,calc(100vw - 32px));margin-left:calc(50% - min(680px,50vw - 16px));}
.tablewrap.wide table{min-width:0;width:100%;table-layout:fixed;font-size:.84rem;}
.tablewrap.wide th,.tablewrap.wide td{white-space:normal;overflow-wrap:anywhere;padding:.5rem .55rem;}
.tablewrap.wide td:first-child{font-weight:600;white-space:nowrap;}
@media(max-width:900px){.tablewrap.wide{width:auto;margin-left:0;}.tablewrap.wide table{min-width:820px;table-layout:auto;}}
.acc-free{color:var(--success);font-weight:600;white-space:nowrap;}
.acc-live{color:var(--accent-dark);font-weight:600;white-space:nowrap;}
.acc-paid{color:var(--warn);font-weight:600;white-space:nowrap;}
.acc-blocked{color:#b42318;font-weight:600;white-space:nowrap;}
.acc-unv{color:var(--ink-muted);font-weight:600;white-space:nowrap;}
.chip{display:inline-block;background:var(--accent-light);color:var(--accent-dark);font-size:.72rem;
font-weight:600;padding:.1rem .45rem;border-radius:100px;margin-left:.3rem;vertical-align:middle;}
.case{background:#fff;border:1px solid var(--border);border-radius:12px;padding:20px 22px;margin:14px 0;}
.case h3{margin:0 0 .4em;font-family:'DM Serif Display',serif;font-size:1.1rem;}
.case p{margin:.5em 0;}
.legend{font-size:.85rem;color:var(--ink-muted);margin:.4em 0 1em;}
.legend span{margin-right:1em;}
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
    <div class="badge">30 states live &middot; updated September 2026</div>
    <h1>What VeriflowAPI actually verifies</h1>
    <p class="sub">Every state we cover, the board each result comes from, how fresh it is,
    and the specific limits of each source. Federal identity and exclusion screening runs
    nationwide on every check. For the states we do not cover yet, and why, see
    <a href="/research/state-license-data-sources.html">where US licence data comes from,
    state by state</a>.</p>
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
        title="License Verification Coverage: 30 States, Board by Board | VeriflowAPI",
        desc="Every state VeriflowAPI verifies, the board each result comes from, how often "
             "it refreshes, and the honest limits of each source. Plus nationwide NPPES and "
             "OIG screening on every check.",
        body=body,
        cta_h="Verify a provider in any of these states",
        qas=[
            ("Which states can VeriflowAPI verify licenses in?",
             "Thirty states today: Texas, Florida, Illinois, Washington, Colorado, "
             "Connecticut, Alabama, New York, Pennsylvania, Ohio, California, Michigan and "
             "New Jersey and Delaware. "
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
    today, and physicians in thirty. The <a href="/coverage.html#professions">role matrix</a>
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
             "roles across 30 states.",
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


# --- Research: state licence data sources ------------------------------------
# One long reference page about what the STATES publish (for everyone, including states we do not
# cover), as opposed to coverage.html, which is about what WE verify. Every row and every claim
# traces to docs/research/ in the API repo (README.md, state-*.md, tail-states-sweep.md), researched
# 2026-09-07. Where that research marks something inferred or unverified, the row says so.
#
# Columns: abbr, name, physicians source, behavioural-health / therapy source, access label, notes.
# Access labels: Free bulk | Live lookup | Paid | Blocked | Unverified (and combinations).
LIVE_ON_VERIFLOW = {"TX", "FL", "IL", "WA", "CO", "CT", "AL", "NY", "NJ", "DE", "PA", "OH", "CA",
                    "MI"}

SOURCES = [
    ("AL", "Alabama",
     "Board of Medical Examiners roster of active licences (dashboard.albme.gov, an ASP.NET "
     "roster postback). Free.",
     "Not researched.",
     "Free bulk",
     "The roster lists currently active licences only, so it confirms present standing and "
     "cannot show a lapsed or revoked licence; absence is not a negative finding."),
    ("AK", "Alaska",
     "DCCED Division of Corporations, Business and Professional Licensing search. Every path "
     "returns 403 from DataDome, with the cookie scoped to all of alaska.gov.",
     "Same agency, same block.",
     "Blocked",
     "gis.data.alaska.gov is open but carries only business licences, no professional-licence "
     "dataset. No Socrata portal."),
    ("AZ", "Arizona",
     "Arizona Medical Board: Cloudflare managed challenge on azmd.gov, an Azure Application "
     "Gateway 403 plus a robots.txt Disallow: / on the GL Suite verification host. The "
     "osteopathic board is on Thentia Cloud behind an AWS WAF CAPTCHA.",
     "Board of Behavioral Health Examiners, Psychology, PT and OT boards: Cloudflare challenge "
     "on every board site and an AWS WAF CAPTCHA on every Thentia tenant (tenant names inferred "
     "from search results, since no board site could be read). SLP sits with the Dept of Health "
     "Services, also behind Cloudflare.",
     "Blocked",
     "No open-data portal (data.az.gov does not resolve). The medical board's own pages, which "
     "could not be read directly, describe a physician and PA database sold on CD-ROM for $100 "
     "with unpublished columns. Three bot-defence products across three hosting stacks."),
    ("AR", "Arkansas",
     "Arkansas State Medical Board lookup: name or licence-number search only, also covers OT.",
     "One shared portal covers psychology, counselling and MFT, and "
     "SLP as well. Social work and PT sit behind "
     "portal.arkansas.gov and were not verified.",
     "Live lookup",
     "No bulk file, no Socrata domain. Three to four separate systems for eight professions."),
    ("CA", "California",
     "Department of Consumer Affairs public licensee files for the Medical Board and "
     "Osteopathic Medical Board, refreshed the 1st of each month, fetched through a public Box "
     "token minted at dca.ca.gov. The DCA iServices JSON API needs a manually approved key; "
     "the search site search.dca.ca.gov is WAF-blocked.",
     "Board of Psychology and Board of Behavioral Sciences (LCSW, LMFT, LPCC) files in the same "
     "monthly release, plus PT and OT boards. The Speech-Language Pathology board's file is "
     "published empty.",
     "Free bulk",
     "The six agency files are tab-delimited despite their spreadsheet extension. Status "
     "vocabulary is Current, Delinquent and Current Inactive. No disciplinary history in the "
     "files; that is only in the API."),
    ("CO", "Colorado",
     "Department of Regulatory Agencies (DORA) professional and occupational licence dataset on "
     "data.colorado.gov (Socrata), refreshed daily.",
     "Same dataset: psychology, clinical social work, professional counselling, MFT, PT, OT, SLP.",
     "Free bulk",
     "Profession is encoded as a licence-type prefix rather than a readable name, so a "
     "prefix-to-profession map is needed before the file is useful."),
    ("CT", "Connecticut",
     "Department of Consumer Protection licence and credential dataset on data.ct.gov (Socrata), "
     "refreshed daily, health professions alongside every other regulated occupation.",
     "Same dataset.",
     "Free bulk",
     "One combined name field rather than first and last, and credential numbers are reused "
     "across record types, so rows must be split and deduplicated to one per credential."),
    ("DE", "Delaware",
     "Division of Professional Regulation dataset on data.delaware.gov (Socrata, pjnv-eaih): "
     "353,352 rows, all professions in one file, refreshed each morning. Free.",
     "Same file: Psychology, Social Work Examiners, Mental Health, PT, OT, Speech and Hearing.",
     "Free bulk",
     "The file's own disciplinary_action column is the literal N on every row statewide, "
     "revoked licences included. The separate register (dz6p-akeq) joins on licence number and "
     "is the truth. No NPI, no date of birth."),
    ("DC", "District of Columbia",
     "DC Health HRLA verification portal, Salesforce-hosted.",
     "Same portal: all eight professions including audiology and SLP.",
     "Live lookup",
     "Verified negative on bulk: the full Open Data DC catalogue (1,885 datasets) has no "
     "health-professional licensee dataset, only business, DMV, alcohol and cannabis. No "
     "Socrata domain."),
    ("FL", "Florida",
     "Department of Health MQA licensure data download "
     "(data-download.mqa.flhealthsource.gov), a full file of roughly 1.5 million licensees "
     "across 180-plus professions, behind an account sign-in.",
     "Same file.",
     "Free bulk",
     "Carries dedicated out-of-state telehealth registration categories as their own licence "
     "types."),
    ("GA", "Georgia",
     "Composite Medical Board: live lookup is reCAPTCHA v2. The physicians (MD and DO) data "
     "file costs $500 per snapshot, ordered on a form, emailed, no refresh cadence, and carries "
     "Status, Public Board Action and Date of Action columns.",
     "Six boards under the Secretary of State's GOALS portal (Salesforce Experience Cloud) with "
     "reCAPTCHA v3 and a v2 fallback. The only bulk product described is a $3,000 roster mailed "
     "on CD and paid by cheque (read from search snippets; sos.ga.gov could not be fetched).",
     "Paid / Blocked",
     "Free and current: monthly Public Board Actions PDFs from 2005 to the present, a mix of "
     "text and scanned pages. The data-file licence forbids distribution for the purpose of "
     "resale. A free third-party mirror exists but is frozen at a 2019 extract."),
    ("HI", "Hawaii",
     "DCCA Professional and Vocational Licensing search: 403 with a Cloudflare interstitial "
     "on the search path.",
     "Same consolidated agency, same challenge.",
     "Blocked",
     "Bulk availability unknown because the pages that would describe it sit behind the same "
     "challenge."),
    ("ID", "Idaho",
     "Division of Occupational and Professional Licenses eDOPL portal on FAST Enterprises: "
     "public tiles for individual search, a bulk list search and a discipline search. "
     "The search could not be exercised outside a browser in testing, a "
     "protocol gap rather than a block.",
     "Same portal and the same 48-board dropdown.",
     "Live lookup (unproven)",
     "The app config declares a reCAPTCHA type without rendering one on the public search, so "
     "the posture could change. Whether the bulk-list tile exports a file is unverified. "
     "Eleven real status strings including Canceled, Not Granted and Unlicensed."),
    ("IL", "Illinois",
     "IDFPR licensee database on data.illinois.gov (Socrata, pzzh-kp68), roughly 4.2 million "
     "records, refreshed daily. IDFPR is recognised by the Joint Commission and NCQA as an "
     "approved primary source.",
     "Same dataset. A single social-work category rather than a separate clinical designation.",
     "Free bulk",
     "The status TERMINATED VALID REASON means an ended licence; any substring test that "
     "treats the word valid as active will misreport it (1,642 licences in one measurement)."),
    ("IN", "Indiana",
     "Professional Licensing Agency on MyLicense (mylicense.in.gov): 403 from Cloudflare. Bulk "
     "download is paid: $150 for the first record and $10 per additional 1,000.",
     "Same agency, same block and the same paid file.",
     "Paid / Blocked",
     "The paid file's documented fields are name, licence number, address, issue date, "
     "expiration date and status."),
    ("IA", "Iowa",
     "Board of Medicine on an AMANDA (Granicus) single-page application. The public licence-query route was not located in the "
     "bundles.",
     "Bureau of Professional Licensure on a second AMANDA portal for psychology, social work, "
     "counselling, PT, OT and SLP.",
     "Unverified",
     "The agency consolidated; the verification systems did not. At least six platforms across "
     "the health boards. No bulk file found."),
    ("KS", "Kansas",
     "Board of Healing Arts (MD, DO, PT, OT): a plain lookup form that "
     "returns result rows.",
     "Behavioral Sciences Regulatory Board on a MyLicense/Versa portal: psychology, social work, LPC, LMFT.",
     "Live lookup",
     "The statewide portal prolicenseverify.ks.gov has a JSON search with a CSV flag, but it is "
     "reCAPTCHA-gated. SLP sits with the health department, unverified. No bulk file."),
    ("KY", "Kentucky",
     "Board of Medical Licensure: the verification app returned a 500 at the path tried, and the "
     "board's own page describes purchasing a verification. Unverified.",
     "Social work has a working lookup; the same URL "
     "shape returned 404 for six other boards, so each must be found individually.",
     "Live lookup (partial)",
     "Separate board per profession, several applications, nothing blocked. No bulk file, no "
     "Socrata domain."),
    ("LA", "Louisiana",
     "State Board of Medical Examiners publishes a free monthly Official List of Active "
     "Licensees as a 30.9 MB, 1,265-page PDF with a real text layer: 50,600 records, "
     "physicians, compact physicians, PAs, OT and OTAs. The live portal is invisible "
     "reCAPTCHA v2.",
     "Psychologists: a search interface that returns disciplinary-action and "
     "board-order flags. Social work: a plain HTML form whose robots.txt is Disallow: /. "
     "LPC/LMFT, PT and SLP boards: 403 from an AWS load balancer on every path.",
     "Free bulk / Live / Blocked",
     "The PDF has no status column; it is active-only. Extracting it with pdftotext in layout "
     "mode inserts spaces mid-word and silently corrupts names; raw mode does not. Five boards "
     "run on Cicero Licensing. No open-data portal."),
    ("ME", "Maine",
     "ALMS Online, one query application shared "
     "by the Office of Professional and Occupational Regulation and the medical and osteopathic "
     "boards.",
     "Same form: the regulator dropdown includes psychologists, social workers, counselling "
     "professionals, PT, OT and speech, audiology and hearing.",
     "Free bulk / Live",
     "The state's own help page documents downloading a search result to a comma-delimited "
     "file, so a per-regulator export is a free bulk mirror."),
    ("MD", "Maryland",
     "Board of Physicians publishes free CSVs on the 1st of each month "
     "(doctor_list_revised.csv, allied_health_list.csv, inactive and emeritus rosters). The "
     "live profile carries orders, pending charges and malpractice, "
     "under a disclaimer that commercial use is not appropriate.",
     "Five Dept of Health boards on mdbnc.health.maryland.gov (two on the OARS platform, three "
     "on legacy ASP.NET), each stating it is a primary source updated "
     "daily. Occupational Therapy is on MyLicense and answers Please solve the CAPTCHA.",
     "Free bulk / Live",
     "The physician CSV holds only Active and Probation rows (48,632 and 56), one row per "
     "practice area, and was a month stale on the day it was checked. "
     "No health-practitioner roster on opendata.maryland.gov."),
    ("MA", "Massachusetts",
     "Board of Registration in Medicine: an open physician-profile service returning NPI, four "
     "categories of disciplinary action, and malpractice history.",
     "Dept of Public Health boards on a MyLicense portal. The host refused TCP connections "
     "from two independent networks, so it is unverified; the site's own indexed help text "
     "describes a free data-file download of search results.",
     "Live lookup / Unverified",
     "The best physician source found in any state and the only one publishing NPI. Surname "
     "matching is by prefix and results cap at 5,000 rows, so always send a first name. "
     "mass.gov itself is Akamai-403 to automated clients."),
    ("MI", "Michigan",
     "LARA's MiPLUS portal, Accela-hosted: a live lookup with a detail page per licence. No "
     "bulk file exists.",
     "Same portal: psychology, social work, counselling, MFT, PT, OT, SLP.",
     "Live lookup",
     "The results grid stops at 50 rows with no pager, sorted by licence type, so a common "
     "surname hides rows. Active - In Late Renewal means the expiry has passed. No NPI. "
     "www.michigan.gov returns 403 to datacenter addresses."),
    ("MN", "Minnesota",
     "Board of Medical Practice redirects to a Radware Bot Manager CAPTCHA.",
     "Behavioral Health and Therapy boards: the same Radware CAPTCHA. The Dept of Health "
     "occupations lookup returns 403.",
     "Blocked",
     "Fragmented and protected: a separate board per profession, all behind bot defence. No "
     "bulk file found."),
    ("MS", "Mississippi",
     "State Board of Medical Licensure: reCAPTCHA v2 on the free search (a postback answered "
     "You did not pass CAPTCHA validation). A $300 roster CSV of current licensees with no "
     "status column, and a $500-per-year profile licence that prohibits use in any web "
     "application; both prohibit resale.",
     "Psychology, LPC and PT boards on classic ASP; Social Work and MFT, and the Dept of "
     "Health licensure for OT and SLP, on the state's LARS WebForms platform. All five open, "
     "updated daily.",
     "Live lookup / Blocked",
     "The exact inverse of Oregon. The psychology register publishes no status field at all. "
     "OT/SLP rows encode the profession only in the licence-number prefix and use 12/31/9999 "
     "as a never-expires sentinel. A Public Records Act request is the resale-clause-free route."),
    ("MO", "Missouri",
     "Division of Professional Registration's MOPRO portal on Salesforce Experience Cloud "
     ", one search across 38 boards. It is a JavaScript application whose search calls could not "
     "be characterised without a browser session.",
     "Same portal.",
     "Unverified",
     "reCAPTCHA v3 is loaded on every page; whether the search enforces it is unknown. A "
     "license-downloads page exists but renders nothing without JavaScript. The pre-2025 free "
     "listings at pr.mo.gov are gone (404)."),
    ("MT", "Montana",
     "Dept of Labor and Industry, consolidated: an Accela shell for applications, and a public "
     "lookup on ebizws.mt.gov that returns an F5 Request Rejected page on every path.",
     "Same portal, same block.",
     "Blocked",
     "Montana's own pages say a free licensee list by licence type can be downloaded from the "
     "lookup. It exists; the WAF is in front of it."),
    ("NE", "Nebraska",
     "DHHS Licensure Unit, consolidated, on MyLicense/Versa (the renewal host answers). The "
     "public lookup host was unreachable from the research network.",
     "Same system.",
     "Unverified / Paid",
     "Practitioner lists are sold through the state eGov list service; price unverified."),
    ("NV", "Nevada",
     "Board of Medical Examiners: an F5 Shape JavaScript challenge on the verify page, and a "
     "Thentia Cloud tenant behind an AWS WAF.",
     "PT board on Thentia (AWS WAF). MFT and counsellor board on Certemy (unverified). Social "
     "work on classic ASP, unreachable. Psychology points to the PSYPACT registry.",
     "Blocked",
     "Separate board per profession, mid-migration onto two vendors that both front with bot "
     "defence. The PT board sells a licensee mailing list, price not stated."),
    ("NH", "New Hampshire",
     "Office of Professional Licensure and Certification publishes one free .xlsx of every "
     "licensee: 198,312 rows, 9 columns, no registration, no fee, no licence agreement. Every "
     "nh.gov host returned an Akamai 403 to a non-browser client, so the file was read from an "
     "archive copy.",
     "Same file: Mental Health, Psychology and Allied Health umbrellas. The live portal is "
     "MyLicense behind a JavaScript proof-of-work challenge that sniffs for headless clients.",
     "Free bulk (unreachable) / Blocked",
     "The file holds current licences only: 97.8% Active, zero Expired, zero Revoked, one "
     "Suspended. Observed refresh dates: Feb 2025, May 2025, Dec 2025, Aug 2026. The URL "
     "changes on every refresh. Discipline is published separately per board."),
    ("NJ", "New Jersey",
     "Division of Consumer Affairs bulk roster on MyLicense (newjersey.mylicense.com, "
     "Verification_Bulk): pipe-delimited, one download per profession, confirmed on a charge "
     "screen that reads $0.00. Around 342,000 rows across eight professions.",
     "Same roster: Psychology, Social Work Examiners, Marriage and Family Therapy (which also "
     "holds professional counselors), PT, OT, Audiology (which holds SLP).",
     "Free bulk",
     "43 status values. No discipline column; the Board Action flag exists only on the live "
     "detail page. Literal pipe characters inside address fields shift a few rows. Roughly one "
     "row in seven is an application with no licence number. Contains licensee email."),
    ("NM", "New Mexico",
     "NM Medical Board community on a shared Salesforce tenant "
     "(path inferred, not verified).",
     "Regulation and Licensing Dept boards on the same tenant; the public search page responds.",
     "Live lookup",
     "The old GL Suite host is dead. No free bulk found; formal verifications go through a paid "
     "third party (inferred)."),
    ("NY", "New York",
     "Office of the Professions online verification, search-only, no bulk file.",
     "Same service: psychology, social work, mental health counselling, MFT, PT, OT, SLP, with "
     "enforcement actions for the non-physician professions.",
     "Live lookup",
     "A New York licence does not expire; the triennial registration does. Physician discipline "
     "sits with the Dept of Health's Office of Professional Medical Conduct. Common surnames "
     "time out."),
    ("NC", "North Carolina",
     "Medical Board: Cloudflare Turnstile above the search button. A $150 monthly Excel roster "
     "with unpublished columns and a no-resale clause, and a DataLiNC monitoring subscription "
     "with no published price.",
     "Psychology: reCAPTCHA enforced server-side on a JSON API. Social work: image CAPTCHA "
     "(iGov). Counselors: Turnstile. MFT: reCAPTCHA v2 (LearningBuilder). PT: Cloudflare "
     "block. OT: open Telerik grid. SLP: open, same vendor product as the medical board "
     "without the Turnstile.",
     "Blocked / Live (OT, SLP)",
     "Eight boards on five platforms. The OT grid has no status column, only Good standing, "
     "even on a licence expired in 2012. PT compact privileges are not in the PT board's data."),
    ("ND", "North Dakota",
     "Nothing verified: every board host resolved to a research-sandbox sinkhole address.",
     "Same.",
     "Unverified",
     "From search results only: one small board per profession sharing an identical classic-ASP "
     "verify layout, which suggests one vendor. No evidence of any WAF, only of a network path "
     "that could not get out."),
    ("OH", "Ohio",
     "eLicense Ohio, a Salesforce-hosted live lookup. An official DataOhio daily CSV of all "
     "boards exists behind an OH|ID access request.",
     "Same system: Psychology; Counselor, Social Worker and MFT Board; OT/PT/AT Board; Speech "
     "and Hearing Professionals Board.",
     "Live lookup",
     "Headline status is coarse (Active, Inactive, Closed); the sub-status carries Expired, "
     "Lapsed, Suspended or Retired. Over-broad searches return null. eLicense states that the "
     "Joint Commission and NCQA accept its online status as primary source."),
    ("OK", "Oklahoma",
     "State Board of Medical Licensure and Supervision (also PT, OT, SLP): 403 from an AWS load "
     "balancer, plus a published policy that data mining results in IP blocking, with a "
     "subscriber service at an unpublished price.",
     "Behavioral Health Licensure (LPC/LMFT) on Thentia Cloud behind an AWS WAF. Psychology: "
     "a plain web form. Social work: platform unverified.",
     "Blocked / Paid",
     "No Socrata domain. The one open board covers one profession."),
    ("OR", "Oregon",
     "Oregon Medical Board in-house ASP.NET WebForms lookup: open, covers all current and "
     "former licensees, board actions with linked order PDFs, and a statement that it is a "
     "primary source per Joint Commission and NCQA standards. Terms of service say personal "
     "and non-commercial use; bulk access is by email request.",
     "Psychology, LPC/LMFT, social work, PT, OT and SLP boards are all Thentia Cloud tenants "
     "returning an AWS WAF Human Verification page. Each sells a one-off Excel snapshot: $35 by "
     "cheque (psychology, counselling), $100 (PT, OT), link expiring after seven days.",
     "Live / Blocked / Paid",
     "The historical medical board download no longer exists; the only Socrata dataset is "
     "aggregate licence counts. Only the psychology board's list offers a discipline column. "
     "The search returns 526 rows for a common surname in one page, with no cap."),
    ("PA", "Pennsylvania",
     "PALS live lookup, one search across every board. No bulk file.",
     "Same system: Psychology, Social Workers/MFTs/Professional Counselors, PT, OT, SLP.",
     "Live lookup",
     "Names match by prefix, results cap at 500, every licence a person ever held is returned "
     "with expired training permits often first, discipline is empty unless the detail call "
     "carries the person id, and the API returns licensee email and phone."),
    ("RI", "Rhode Island",
     "Dept of Health on a MyLicense/Versa portal, 517 "
     "licence types in one dropdown.",
     "Same portal: Psychology, Social Work, MFT and mental health, PT, OT, SLP.",
     "Live lookup",
     "No export control on the page; a naive GET returns Invalid search criteria, the real "
     "search is a POST with the standard MyLicense field names."),
    ("SC", "South Carolina",
     "Labor, Licensing and Regulation: one in-house ASP.NET WebForms app for 46 boards, with "
     "reCAPTCHA v2 in the shared search control, continuously CAPTCHA-gated since about 2013 "
     "(BotDetect before that).",
     "Same app, same control, same site key.",
     "Blocked / Paid",
     "No bulk file, free or paid, on the domain. Each board sells a $10 licensee list by "
     "cheque, delivered by email or CD, under a signed anti-commercial-solicitation "
     "certification (Code section 30-2-50). The LLR hosts were TCP-unreachable from two "
     "networks; findings are from archived pages."),
    ("SD", "South Dakota",
     "Board of Medical and Osteopathic Examiners (also PT and OT): a Blazor Server app over a "
     "stateful SignalR circuit plus an explicit reCAPTCHA.",
     "Social work, psychology and counsellor boards under Social Services: unreachable from "
     "the research network, unverified.",
     "Blocked / Unverified",
     "Blazor Server is the least tractable platform seen; there is no plain request to replay "
     "even before the CAPTCHA."),
    ("TN", "Tennessee",
     "Dept of Health, Division of Health Related Boards: one verification system for all "
     "boards, which returns a bare 403 from an AWS load balancer on "
     "every path including robots.txt, from two independent networks.",
     "Same host, same 403.",
     "Unverified / Blocked",
     "Structurally the best state in the round: one department, daily refresh and a Licensure "
     "Reports builder that one search snippet describes as a bulk export, all unverified. Claims "
     "of a $0.02-per-query state API come from SEO spam, not tn.gov."),
    ("TX", "Texas",
     "Texas Medical Board public verification portal, a live lookup. No bulk file.",
     "Not researched.",
     "Live lookup",
     "Training permits are listed alongside full licences, and a physician who trained in "
     "Texas often holds both."),
    ("UT", "Utah",
     "Division of Professional Licensing: the free lookup uses reCAPTCHA "
     "v3 and escalates to an interactive v2 checkbox after a rejected submit. A self-service "
     "data request sells the full list at $0.01 per record (minimum $5) with Disciplinary "
     "Action and Docket Numbers columns and a last-updated filter for deltas.",
     "Same division, same lookup, same file.",
     "Paid / Blocked",
     "The lookup itself runs off a nightly snapshot (Information Current as of the previous "
     "day). dopl.utah.gov, including its data-download page, is behind a Cloudflare "
     "interstitial. No Socrata or CKAN portal."),
    ("VT", "Vermont",
     "Board of Medical Practice dataset on Socrata (vtmbl-reporting.data.socrata.com, "
     "mxkz-bi85): 25,794 rows covering physicians, PAs and podiatrists, refreshed daily. Free.",
     "Office of Professional Regulation Pega portal: 403 from an F5 device. The state's docs "
     "describe a Profession Roster Download tab inside it.",
     "Free bulk / Blocked",
     "The physician file's actions column takes only two values across the whole dataset, None "
     "and Comments, so it is a weak flag rather than a history."),
    ("VA", "Virginia",
     "Dept of Health Professions lookup, one record per occupation-coded licence "
     "number, refreshed each "
     "business day. Banner reads Not For Commercial Use with a volume limit; a $95 per user "
     "per year License Verification Subscription is the stated route for regular use.",
     "Same lookup, all eight professions under thirteen boards.",
     "Live lookup (subscription)",
     "The paid bulk extract ($100 plus $20 per 1,000 records, UTF-16LE) has no status column. "
     "The Additional Public Information flag can include proceedings with a finding of no "
     "violation. Licences that expired before 2000 are not searchable."),
    ("WA", "Washington",
     "Dept of Health health-care provider credential dataset on data.wa.gov (Socrata): about "
     "2.4 million credentials, refreshed daily.",
     "Same dataset, including mental health counsellors, social workers, MFTs, psychologists, "
     "PT, OT, SLP and state-licensed behavior analysts.",
     "Free bulk",
     "One of the few states licensing behavior analysts at state level."),
    ("WV", "West Virginia",
     "Board of Medicine and osteopathic board hosts were sinkholed by the research network; "
     "unverified.",
     "Social work: a WebForms lookup. Psychology: a SharePoint lookup. "
     "Counseling (LPC and LMFT): Certemy, needs an anonymous token from the bundle. PT: "
     "Cloudflare 403. OT: a WordPress 500 on the verify page, with a mailing-list request.",
     "Live (partial) / Unverified",
     "Eight-plus separate boards, no free bulk file."),
    ("WI", "Wisconsin",
     "Dept of Safety and Professional Services, consolidated. Every wi.gov name failed DNS in "
     "the research sandbox, so the platform (Salesforce, from the URL shape) is inferred.",
     "Same system.",
     "Paid / Unverified",
     "The credential list is $2,000 for all types plus $4 per 1,000 records, free to government "
     "agencies on request."),
    ("WY", "Wyoming",
     "Board of Medicine on GL Suite: 403 with an Azure WAF title.",
     "Mental Health Professions (LPC, LCSW, LMFT), Psychology and SLP boards publish their "
     "rosters as public Google Sheets; the CSV export links return real rows. PT and OT boards "
     "were not located.",
     "Free bulk (5 of 8) / Blocked",
     "The psychology sheet states its own last-update date and calls itself a primary source. "
     "Hand-maintained sheets carry junk header rows above the real header."),
]

_ACCESS_CLASS = [("Blocked", "acc-blocked"), ("Paid", "acc-paid"), ("Unverified", "acc-unv"),
                 ("Free bulk", "acc-free"), ("Live", "acc-live")]


def _access_class(label: str) -> str:
    # First label wins, so a "Free bulk / Blocked" row reads as a free-bulk state.
    for key, cls in _ACCESS_CLASS:
        if label.startswith(key):
            return cls
    return "acc-unv"


def research_page() -> str:
    rows = "".join(
        f'<tr id="src-{abbr.lower()}"><td><strong>{name}</strong>'
        + ('<span class="chip">verified by us</span>' if abbr in LIVE_ON_VERIFLOW else "")
        + f'</td><td>{phys}</td><td>{bh}</td>'
        f'<td class="{_access_class(access)}">{access}</td><td>{notes}</td></tr>'
        for abbr, name, phys, bh, access, notes in sorted(SOURCES, key=lambda r: r[1]))

    body = f"""  <section class="hero">
    <div class="badge">Research &middot; last researched September 2026</div>
    <h1>Where US licence data comes from: a state-by-state map</h1>
    <p class="sub">Which states publish healthcare licensee data, in what form, who charges for it,
    who blocks automated access, and the data-quality traps inside the files. All 50 states and
    DC, with URLs, platforms and prices.</p>
    <p class="muted" style="font-size:.9rem;max-width:660px">This page is about what the
    <em>states</em> publish, for anyone who needs it. It covers states VeriflowAPI does not verify.
    For what we verify today, see the <a href="/coverage.html">coverage page</a>. Facts were checked
    on 7 September 2026 with ordinary HTTP requests; nothing behind a CAPTCHA or WAF was probed
    further, and anything read from a search snippet or an archive rather than the live site is
    labelled inferred or unverified.</p>
  </section>

  <section>
    <h2>The three ways a state publishes licence data</h2>
    <p>Every US licensing board holds the same core record: a person, a licence number, a type, a
    status, an issue date, an expiry date, and usually some indicator of discipline. How that record
    reaches the public falls into three shapes, and the shape decides how fresh and how reliable a
    downstream verification can be.</p>
    <h3>1. A free bulk file</h3>
    <p>The best case is a whole-database export on a schedule. Delaware puts its entire Division of
    Professional Regulation database on Socrata (<code>data.delaware.gov</code>, dataset
    <code>pjnv-eaih</code>): 353,352 rows, every profession, refreshed each morning. Illinois,
    Washington, Colorado and Connecticut do the same on their own Socrata portals. Vermont does it
    for physicians only (25,794 rows on <code>vtmbl-reporting.data.socrata.com</code>). A federated
    catalogue search across the 23 least-requested states found licensee datasets on exactly two
    Socrata domains, Delaware's and Vermont's; Nevada, West Virginia, Kansas, South Dakota, Wyoming,
    North Dakota, Arkansas, Oklahoma, Alaska and DC have no Socrata portal at all.</p>
    <p>Bulk also arrives in less tidy containers. Maryland's Board of Physicians publishes CSVs on the
    1st of each month with seven preamble lines before the header. Louisiana's medical board
    publishes a 1,265-page PDF every month. New Hampshire publishes a 13 MB <code>.xlsx</code> whose
    filename carries its as-of date. New Jersey's roster is a pipe-delimited text file generated on
    demand behind a confirmation screen that charges $0.00. Wyoming's small boards publish Google
    Sheets. Each of these is a real, free, complete file, and each needs its own parser.</p>
    <p>A bulk file makes verification fast and lets you see the whole population, but it is only as
    fresh as the state's publication schedule, which ranges from every morning (Delaware) to
    roughly quarterly with an eight-month gap observed (New Hampshire). A mirror must carry the
    file's as-of date, or a licence revoked after the last export reads as active.</p>
    <h3>2. A live lookup portal</h3>
    <p>Most states publish no file and offer a search form instead. What the form runs on matters
    more than what it looks like: an ASP.NET WebForms application (Texas, Oregon's medical board,
    Maine), an Accela portal (Michigan), a Salesforce community (Ohio, Missouri,
    DC, New Mexico), a MyLicense/Versa instance (Rhode Island, Kansas, Nebraska), or a JavaScript search
    application (Pennsylvania, New York, Massachusetts physicians, Louisiana psychologists). A live lookup
    is as fresh as the board's own database, often same-day, but every check is a round trip to a
    server you do not control, the result may be capped or prefix-matched, and a board can turn on
    bot defence overnight without notice.</p>
    <h3>3. Nothing usable</h3>
    <p>The third shape is a search form behind an interactive CAPTCHA or a web application
    firewall, with either no bulk product or one that arrives by post. Arizona's every board sits
    behind Cloudflare, an AWS WAF CAPTCHA or an Azure gateway 403, and the one purchasable file is a
    CD-ROM. South Carolina has CAPTCHA-gated all 46 of its boards continuously for more than a
    decade. Georgia's Secretary of State roster is, by the state's own description, a $3,000 CD
    paid by cheque. For a verification
    product that does not solve CAPTCHAs or evade firewalls, these states are not slow; they are
    unavailable, and the only honest routes are a public-records request, a data agreement, or a
    sanctioned API key from the vendor.</p>
  </section>

  <section>
    <h2>The platform effect: the vendor decides, not the profession</h2>
    <p>An easy assumption is that physician data is open because medical boards are large and well
    funded, and behavioural-health data is closed because counselling boards are small. The
    evidence does not follow profession lines. It follows which software vendor each board
    consolidated onto, which is a procurement accident.</p>
    <p>Oregon and Mississippi are exact inverses. In Oregon the medical board runs an in-house
    ASP.NET lookup that is open, returns board actions with linked order PDFs, and describes itself
    as a primary source per Joint Commission and NCQA standards; the six psychology, counselling,
    social work, PT, OT and SLP boards all moved to Thentia Cloud, and every one of their tenants
    returns an AWS WAF Human Verification page. In Mississippi the medical board is the one with
    reCAPTCHA v2 on its search, while the psychology, counselling, social work and MFT, PT, and
    health department OT/SLP registers all run on in-house or state-IT software and are wide open,
    updated daily. South Carolina blocks both equally with one shared control.</p>
    <p>What each platform typically means, from the states where it was confirmed:</p>
    <div class="grid">
      <div class="card"><h3>Socrata open data</h3><p>Free, daily, whole-database CSV or JSON with
      no login. Delaware, Illinois, Washington, Colorado, Connecticut, Vermont physicians.</p></div>
      <div class="card"><h3>Accela</h3><p>A hosted citizen-portal product with a search form and a detail page per licence.
      Michigan. Montana
      uses Accela for applications but moved its public lookup behind an F5 firewall.</p></div>
      <div class="card"><h3>Salesforce communities</h3><p>Salesforce-hosted licensing communities: Ohio, DC, New Mexico and Missouri.
      Georgia's GOALS is the same family with reCAPTCHA in front.</p></div>
      <div class="card"><h3>MyLicense / Versa</h3><p>Hosted WebForms with a consistent layout
      (<code>t_web_lookup__*</code>) across instances. Rhode Island, Kansas BSRB, New Jersey
      (with a free bulk roster). Maryland OT and Indiana run the same product with a CAPTCHA or
      Cloudflare in front, so it is per-tenant.</p></div>
      <div class="card"><h3>Thentia Cloud</h3><p>A clean public REST API on paper, but an AWS WAF
      CAPTCHA on every tenant found: Oregon (six boards, confirmed from the boards' own sites),
      Nevada, Oklahoma behavioural health, and Arizona (tenant names inferred). Treat as blocked
      until a sanctioned key exists.</p></div>
      <div class="card"><h3>Shared reCAPTCHA search controls</h3><p>One CAPTCHA widget wired into
      a control every board reuses: South Carolina (46 boards, one site key), Georgia, the
      Mississippi medical board, most of North Carolina.</p></div>
    </div>
    <p>One methodological trap is worth stating because it produced a wrong conclusion once.
    Thentia's WAF answers <em>any</em> subdomain of <code>portalus.thentiacloud.net</code> with the
    byte-identical Human Verification page, including a made-up control name that does not exist.
    Finding that <code>&lt;state&gt;.portalus.thentiacloud.net</code> is WAF-blocked therefore
    proves nothing about whether the state uses Thentia. Tenancy has to be confirmed from the
    board's own site linking to the tenant, which is how the Oregon finding stands and why a
    Thentia hit for South Carolina turned out to be a false positive (its real lookup is an
    in-house application).</p>
  </section>

  <section id="table">
    <h2>State by state: physicians, behavioural health, access</h2>
    <p>The behavioural-health column covers psychology, clinical social work, professional
    counselling, marriage and family therapy, and, where the state groups them the same way,
    physical therapy, occupational therapy and speech-language pathology. States marked
    <span class="chip">verified by us</span> are the fourteen VeriflowAPI verifies today; their
    rows describe the same public source we use, which is also simply what the state publishes.</p>
    <div class="legend">
      <span class="acc-free">Free bulk</span> a complete file at no cost &middot;
      <span class="acc-live">Live lookup</span> a search portal, no bulk file &middot;
      <span class="acc-paid">Paid</span> the usable product costs money &middot;
      <span class="acc-blocked">Blocked</span> CAPTCHA or WAF on the only route &middot;
      <span class="acc-unv">Unverified</span> could not be reached or read on 7 Sep 2026
    </div>
    <div class="tablewrap wide">
    <table>
      <colgroup><col style="width:9%"><col style="width:29%"><col style="width:29%"><col style="width:9%"><col style="width:24%"></colgroup>
      <thead><tr><th>State</th><th>Physicians source</th><th>Behavioural health / therapy source</th>
      <th>Access</th><th>Notes</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </div>
    <p class="muted">Network caveat: the research sandbox could not resolve or connect to several
    state hosts (all of <code>wi.gov</code>, the small North Dakota, South Dakota and West Virginia
    board domains, <code>nebraska.gov</code>, <code>in.gov</code>, and the Massachusetts and South
    Carolina MyLicense and LLR hosts). Those are recorded as unverified, never as blocked, because
    a connection that never left our network says nothing about the state.</p>
  </section>

  <section>
    <h2>Case studies: what the files actually do</h2>
    <div class="case">
      <h3>Georgia: $500, no refresh, and a resale clause</h3>
      <p>The Composite Medical Board's data request page lists eleven priced lists and a custom
      option. Physicians (MD and DO) cost $500; all professions $1,100; each allied group $200. The file is emailed after
      payment and carries Status, First License Date, Expiration Date, Public Board Action and Date
      of Action, which is everything a verification needs except NPI. There is no subscription and
      no published cadence: refresh means buy again. The licence text states that no part of the
      data will be distributed for the purpose of resale, and that the data is provided as is.</p>
      <p>Do not confuse it with the cheaper-looking self-serve roster on the same site, which has no
      Status column and contains only currently licensed practitioners, so a revoked physician
      simply disappears. The six behavioural and therapy boards sit under the Secretary of State's
      GOALS portal with reCAPTCHA v3 and a v2 fallback; the only bulk product described for them is
      a $3,000 roster mailed on CD, payable by cheque or money order, partial lists not available.
      The one free, current Georgia source is the monthly Public Board Actions PDF list, 253
      documents from 2005 onward, useful as a discipline delta but carrying no roster.</p>
    </div>
    <div class="case">
      <h3>Arizona: every board, every stack, blocked</h3>
      <p>Every Arizona board host probed answered with a bot-defence page: a Cloudflare
      managed challenge on the medical, osteopathic, PA, psychology, behavioural health, PT and OT
      board sites and on the health department's SLP search; an AWS WAF CAPTCHA on every Thentia
      tenant, including on <code>/robots.txt</code>; and, on the legacy GL Suite verification host,
      both an Azure Application Gateway 403 and a robots.txt that disallows everything. The only
      purchasable file is the medical board's physician and PA database on a $100 CD-ROM, described
      on pages that could not themselves be read. Speech-language pathology is not board-licensed
      at all in Arizona; it sits with the Department of Health Services.</p>
    </div>
    <div class="case">
      <h3>Delaware: the whole database is free, and one column lies</h3>
      <p>Delaware is the cheapest state to mirror found in this research: one Socrata dataset, all eight
      professions, refreshed daily, with a companion dataset of disciplinary actions. But the
      licence file's own <code>disciplinary_action</code> column reads N on all 353,352 rows,
      revoked licences included. Mapping it would assert a clean record for the entire state. The
      companion register's licence id joins to the file's licence number; 665 disciplined pairs in
      the health professions resolve to exactly one row each, and 212 of those licences are
      currently Active. The file also uses status values such as Non-Disciplinary Suspension, which
      any substring test for the word discipline will read backwards.</p>
    </div>
    <div class="case">
      <h3>New Jersey: a free roster with pipes inside the fields</h3>
      <p>New Jersey's Division of Consumer Affairs directs bulk users away from its verification
      form and to a roster download that is pipe-delimited, unquoted, and space-padded to fixed
      widths. In the 138,115-row physician file, three rows had their status column shifted because
      an address contained a literal pipe: one status cell held an email address, another a city
      name. Validate every status against the 43-value vocabulary and reject rows whose field count
      is wrong, or those rows become silent unknowns. The file has no discipline column; the Board
      Action flag exists only on the live detail page. And Active Reduced Fee 65+ arrives with a
      trailing space.</p>
    </div>
    <div class="case">
      <h3>Michigan: Active, but expired</h3>
      <p>Michigan's MiPLUS portal labels a licence whose expiry date has already passed but which
      is still inside the renewal window as Active - In Late Renewal. Practice is not authorised on
      an expired licence, so a status mapper that keys on the word Active reports a lapsed
      clinician as current. The same portal caps its results grid at 50 rows with no pager, sorted
      by licence type, so for a common surname the health licences can fall off the bottom of the
      grid without any truncation notice. Michigan publishes no bulk file and no NPI.</p>
    </div>
    <div class="case">
      <h3>Illinois: TERMINATED VALID REASON is not valid</h3>
      <p>Illinois writes TERMINATED VALID REASON for a licence that has ended for a legitimate
      reason. A normaliser that tests for the substring valid among its active keywords maps that
      to active; in one measurement it reported 1,642 ended Illinois licences as current. The
      general lesson is that substring status matching must test the negative words (terminated,
      revoked, suspension) before the positive ones, and that qualified statuses (Active - With
      Conditions, Active (With Restrictions), Active On Probation) must raise a discipline signal
      rather than normalise to a clean active.</p>
    </div>
    <div class="case">
      <h3>Massachusetts: the best physician source in the country</h3>
      <p>The Board of Registration in Medicine's public search runs on a public profile service. A
      profile record carries the NPI, original and latest issue dates, expiry, in-state and
      out-of-state board discipline, healthcare-facility discipline and criminal convictions, each
      with dates, case numbers and instrument type, plus malpractice payment history for
      Massachusetts and other states. No other state source found publishes NPI, which caps
      name-only matching everywhere else. The API has a 5,000-row result cap and matches surnames
      by prefix, so a search must always carry a first name. Its status vocabulary includes
      Suspension as a noun, which a test for the verb suspend will miss.</p>
    </div>
  </section>

  <section>
    <h2>What primary source verification actually means here</h2>
    <p>Primary source verification means reading the credential from the body that issued it. Several
    boards say so in their own words: Illinois IDFPR and eLicense Ohio cite Joint Commission and
    NCQA acceptance; the Oregon Medical Board's detail page states it is a primary source consistent
    with those standards; Virginia's DHP says its lookup data serves as primary source verification
    of the credential; the Maryland OARS boards, the Mississippi psychology and counselling boards,
    the North Carolina social work board and even Wyoming's psychology spreadsheet make the same
    claim. A mirror of a board's own published file, stamped with the file's as-of date, is a copy
    of the primary source at a known time. A vendor's mirror of somebody else's mirror is not.</p>
    <p>Freshness is the second half. The same board can expose the same data at very different
    ages: Utah's public lookup prints Information Current as of the previous day, so a purchased
    file is no staler than the state's own search; Maryland's physician CSV was dated 1 August on
    7 September while its allied-health CSV was dated 1 September; Georgia's file is as old as your
    last $500. A third-party physician mirror that is free and open in Georgia turns out to be an
    extract dated 1 May 2019 on every record. Any verification record should carry the date the
    source was read, and any file mirror should carry the date the file was generated.</p>
    <p>The third half is absence. Alabama's roster, Georgia's self-serve roster, Mississippi's $300
    roster, Louisiana's monthly PDF, New Hampshire's spreadsheet and Maryland's physician CSV all
    publish current licensees only. New Hampshire's file has zero Expired, zero Lapsed, zero
    Revoked rows, while the office's own status definitions describe all three. Virginia's lookup
    excludes anything that expired before 2000. In every one of these sources a revoked clinician
    is not marked revoked; they vanish. Absence from a current-licensees roster must be read as
    not found, never as not licensed and never as no discipline.</p>
  </section>

  <section>
    <h2>Commercial-use restrictions a builder must read</h2>
    <p>Several open or purchasable sources carry terms that a commercial user should read before
    building on them. These are reported as text to check, not as legal advice.</p>
    <ul>
      <li><strong>Georgia Composite Medical Board</strong> data file: no part of the data will be
      distributed in any form or by any means for the purpose of resale; any other use constitutes
      unlawful usage. The North Carolina Medical Board's $150 roster and the Mississippi medical
      board's $300 roster use materially the same clause.</li>
      <li><strong>Mississippi medical board</strong> $500-per-year profile licence: for internal
      credentials verification only; use on a website or web application of any kind is strictly
      prohibited. The state's Public Records Act process is the route without a contractual
      clause.</li>
      <li><strong>Maryland Board of Physicians</strong> Practitioner Profile System disclaimer:
      commercial use of this information is not appropriate. The monthly rosters are published
      under a Public Information Act framing instead; whether that separates the two is a question
      for counsel.</li>
      <li><strong>Oregon Medical Board</strong> terms of service: the service is for personal and
      non-commercial use, and users may not copy, distribute, publish or sell information obtained
      from it. The same pages invite bulk-data enquiries by email, which is the route to a written
      exception.</li>
      <li><strong>Virginia DHP</strong> lookup banner: Not For Commercial Use, with volume limits
      and a $95 per user per year subscription for regular or high-volume verification. Whether
      that subscription permits programmatic access is not published.</li>
      <li><strong>AIM DocFinder</strong> (a free third-party physician mirror for several states):
      intended for non-commercial use of the general public only; commercial users may be
      blocked.</li>
      <li><strong>Oklahoma medical board</strong>: the search is not intended for mass harvesting
      and data mining results in IP blocking.</li>
      <li><strong>South Carolina</strong> licensee lists: a signed certification under Code section
      30-2-50 that the records will not be used for commercial solicitation, with a misdemeanour
      penalty. The statute targets solicitation, and the form has an Other box, but it must be
      signed once per board.</li>
      <li><strong>Louisiana social work board</strong>: robots.txt is Disallow: / on the whole
      site. A crawl directive rather than a contract, and worth a written
      permission before automating.</li>
    </ul>
    <p>None of the Socrata states, Delaware, New Jersey, Maine, Kansas, Rhode Island, DC or the
    open Maryland and Mississippi boards were found to publish any restriction on automated access
    in the pages retrieved. That is different from a board having sanctioned it.</p>
  </section>

  <section>
    <h2>Using this page</h2>
    <p>If you are building or buying licence verification, the table above tells you which states
    can be automated at all, which need a purchase order, and which need a phone call. What
    VeriflowAPI verifies today, board by board, is on the <a href="/coverage.html">coverage
    page</a>; the live health of each of those sources is on the <a href="/status.html">status
    page</a>. If a state here matters to you and is not there yet, the research is the reason, and
    the <a href="/">homepage</a> has the contact.</p>
  </section>
"""
    return page(
        path="research/state-license-data-sources.html",
        title="Where US Licence Data Comes From: A State-by-State Map | VeriflowAPI",
        desc="Which US states publish healthcare licensee data, which charge for it, and which "
             "block automated access. All 50 states and DC: URLs, platforms, prices, traps.",
        body=body,
        cta_h="Verify against the sources that can be verified",
        qas=[
            ("Which states publish a free bulk file of healthcare licensees?",
             "Delaware, Illinois, Washington, Colorado and Connecticut on Socrata portals, "
             "refreshed daily; Vermont for physicians only. New Jersey's roster is a free "
             "pipe-delimited download. Maryland's Board of Physicians publishes monthly CSVs. "
             "Louisiana's medical board publishes a monthly PDF of active licensees. California's "
             "Department of Consumer Affairs publishes monthly files per board. New Hampshire "
             "publishes one spreadsheet of every licensee, if you can reach nh.gov. Wyoming's "
             "smaller boards publish Google Sheets. Maine documents a CSV export inside its search."),
            ("Which state medical boards charge for their licensee data?",
             "Georgia sells its physician file for $500 per snapshot and all professions for "
             "$1,100. North Carolina's medical board roster is $150 per month. Mississippi's is "
             "$300 per roster or $500 per year for a profile licence. Arizona's medical board "
             "describes a $100 CD-ROM. Indiana charges $150 plus $10 per 1,000 records. Wisconsin "
             "charges $2,000 plus $4 per 1,000. Utah sells its full list at $0.01 per record with "
             "discipline columns. Virginia's bulk extract is $100 plus $20 per 1,000 but has no "
             "status column. Oregon's non-physician boards sell snapshots at $35 to $100 each."),
            ("Which states block automated access to licence lookups entirely?",
             "Arizona (Cloudflare, AWS WAF and Azure gateway on every board), South Carolina "
             "(reCAPTCHA on all 46 boards), Minnesota (Radware CAPTCHA), Hawaii (Cloudflare), "
             "Alaska (DataDome), Montana (F5 on the public lookup) and Nevada (F5 Shape and "
             "Thentia). Tennessee and New Hampshire return plain 403s whose scope is unknown. "
             "Several other states block one board while leaving others open."),
            ("Does any state board publish NPI numbers?",
             "Only one was found: the Massachusetts Board of Registration in Medicine's public "
             "API returns npiNumber on physician profiles. Every other state source located, "
             "including every Socrata file, MyLicense portal and Thentia tenant, publishes name, "
             "licence number, status and dates but no NPI and no date of birth. South Carolina's "
             "archived detail template shows a birth date field, unconfirmed on the live site."),
            ("Is a state board's online lookup accepted as primary source verification?",
             "Several boards state so explicitly: Illinois IDFPR and eLicense Ohio cite Joint "
             "Commission and NCQA acceptance, the Oregon Medical Board and Virginia DHP make the "
             "same claim, and Maryland's OARS boards describe their data as primary sources "
             "updated daily. A mirror of a board's own published file, stamped with the file's "
             "as-of date, is a copy of the primary source at a known time."),
            ("Why can absence from a state roster not mean the person is unlicensed?",
             "Because many rosters contain current licensees only. Alabama's roster, Georgia's "
             "self-serve roster, Mississippi's $300 roster, Louisiana's monthly PDF, New "
             "Hampshire's spreadsheet and Maryland's physician CSV all omit expired, revoked and "
             "surrendered licences rather than marking them. A revoked clinician vanishes. "
             "Absence must be read as not found, never as not licensed."),
            ("What is Thentia Cloud and why does it matter for licence verification?",
             "Thentia Cloud is a licensing platform that small boards consolidate onto. Every "
             "tenant found, in Oregon (confirmed from the boards' own sites), Nevada, Oklahoma "
             "and Arizona (tenant names inferred), answers with an AWS WAF Human Verification "
             "CAPTCHA. "
             "Its WAF returns the identical page for any subdomain, including made-up ones, so a "
             "WAF hit on a guessed tenant name proves nothing about whether a state uses it."),
            ("How current is state licence data?",
             "It ranges from same-day to indefinitely stale. Delaware refreshes every morning and "
             "Virginia each business day. Utah's own lookup runs off a nightly snapshot. Maryland "
             "promises the 1st of each month and slipped a month. New Hampshire refreshed four "
             "times in eighteen months. Georgia's purchased file is as old as the last order. Any "
             "verification record should carry the date the source was read."),
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
    urls = [coverage_page(), telehealth_page(), credentialing_page(), staffing_page(),
            research_page()]

    for path, target in REDIRECTS.items():
        html = STUB.replace("__TARGET_ABS__", SITE + target).replace("__TARGET__", target)
        write(path, html)

    write_sitemap(urls)
    print(f"{len(urls)} content pages + seo.css; {len(REDIRECTS)} redirect stubs")
    for u in urls:
        print("   ", u)


if __name__ == "__main__":
    main()
