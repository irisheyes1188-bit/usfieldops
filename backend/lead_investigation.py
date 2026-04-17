from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import re
from typing import Iterable
from urllib import error, parse, request


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; FieldOpsLeadInvestigator/1.0; +https://usfieldops.com)"
)
DEFAULT_TIMEOUT_SECONDS = 12
MAX_WEBSITE_PAGES = 8
MAX_SEARCH_RESULTS = 6
CONTACT_PATH_HINTS = (
    "contact",
    "about",
    "team",
    "staff",
    "leadership",
    "company",
    "directory",
    "board",
    "trustees",
    "governance",
    "who-we-are",
    "who-we-serve",
    "our-team",
    "our-staff",
)
ROLE_KEYWORDS = (
    "owner",
    "principal",
    "president",
    "chief executive",
    "executive director",
    "administrator",
    "board",
    "trustee",
    "manager",
    "operations",
    "facility",
    "facilities",
    "director",
    "maintenance",
    "engineering",
    "capital",
    "project",
    "compliance",
    "rebate",
    "program",
    "office",
    "franchise",
    "operator",
    "development",
    "expansion",
)
TITLE_HINTS = (
    "owner",
    "president",
    "chief executive officer",
    "ceo",
    "executive director",
    "chief operating officer",
    "chief financial officer",
    "administrator",
    "board chair",
    "board president",
    "trustee",
    "vice president",
    "director",
    "manager",
    "operations lead",
    "operations manager",
    "facilities manager",
    "facility manager",
    "service manager",
    "service director",
    "estimator",
    "estimating manager",
    "project executive",
    "project engineer",
    "superintendent",
    "office manager",
    "office administrator",
    "program manager",
    "compliance manager",
    "regional manager",
    "general manager",
    "franchise manager",
    "franchisee",
    "operator",
    "development manager",
)
DEPARTMENT_HINTS = (
    ("facilities", "Facilities"),
    ("facility", "Facilities"),
    ("maintenance", "Maintenance"),
    ("operations", "Operations"),
    ("engineering", "Engineering"),
    ("capital projects", "Capital Projects"),
    ("construction", "Construction"),
    ("service", "Service"),
    ("estimating", "Estimating"),
    ("estimator", "Estimating"),
    ("project management", "Project Management"),
    ("project manager", "Project Management"),
    ("administration", "Administration"),
    ("finance", "Finance"),
    ("office", "Administrative Office"),
    ("development", "Development"),
)
NONPROFIT_TOKENS = ("ymca", "y m c a", "foundation", "nonprofit", "non-profit", "charity")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(
    r"(?:\+?1[\s.\-]?)?(?:\(?\d{3}\)?[\s.\-]?)\d{3}[\s.\-]?\d{4}"
)
NAME_ROLE_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*(?:,|-|\u2013|\u2014)\s*([A-Za-z/& ]{3,80})"
)
ROLE_NAME_RE = re.compile(
    r"\b("
    r"(?:Chief Executive Officer|Chief Operating Officer|Chief Financial Officer|Executive Director|President(?:\s*&\s*CEO)?|"
    r"Board Chair|Board President|Trustee|Director|Manager|Administrator|Facilities Manager|Operations Manager|Maintenance Manager|Franchise Manager)"
    r")\s*(?:,|-|\u2013|\u2014|:)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
    re.I,
)
ENTITY_NAME_RE = re.compile(r"\b([A-Z][A-Za-z0-9&' .-]+?,\s+(?:LLC|Inc\.?|Corp\.?|Corporation|Ltd\.?))\b")
SITE_NAME_RE = re.compile(
    r'(?is)<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']'
)
TITLE_RE = re.compile(r"(?is)<title>(.*?)</title>")
QUERY_VARIANTS = (
    "leadership",
    "staff",
    "board of directors",
    "executive director",
    "facilities manager",
    "operations manager",
    "contact",
    "grand opening",
    "franchisee",
    "operator",
    "expansion",
    "llc",
)
NOISY_NAME_PREFIXES = {"us", "our", "meet", "team", "staff", "board", "leadership", "contact"}
PUBLIC_INSTITUTION_TOKENS = (
    "city of",
    "county",
    "school district",
    "public school",
    "state of",
    "department of",
    "university",
    "college",
    "public works",
    "library",
    "housing authority",
    "district",
)
CONTRACTOR_TOKENS = (
    "construction",
    "contractor",
    "builders",
    "builder",
    "mechanical",
    "electric",
    "electrical",
    "plumbing",
    "roofing",
    "excavation",
    "hvac",
    "heating",
    "cooling",
    "sheet metal",
    "engineering",
    "development",
)
RETAIL_TOKENS = (
    "store",
    "market",
    "grocery",
    "restaurant",
    "hotel",
    "resort",
    "pharmacy",
    "bank",
    "credit union",
    "retail",
    "outlet",
    "fitness center",
    "fitness club",
    "oil change",
    "franchise",
)
LOCAL_PRESS_HINTS = (
    "dailyinterlake",
    "nbcmontana",
    "kpax",
    "ktvq",
    "krtv",
    "montanarightnow",
    "billingsgazette",
    "missoulian",
    "helenair",
    "tribune",
    "chronicle",
    "news",
    "interlake",
)
GENERIC_LOCATION_PATH_HINTS = (
    "/locations/",
    "/location/",
    "/stores/",
    "/store/",
)
OPERATOR_SIGNAL_TERMS = (
    "llc",
    "franchisee",
    "franchise manager",
    "operator",
    "grand opening",
    "expansion",
    "owner",
    "opened",
    "opening",
    "rollout",
    "developer",
)
ENTITY_PROFILES = {
    "nonprofit": {
        "label": "Nonprofit / community organization",
        "query_variants": (
            "board of directors",
            "board chair",
            "executive director",
            "ceo",
            "staff",
            "leadership",
            "contact",
            "form 990",
            "facilities manager",
            "operations manager",
        ),
        "link_hints": ("board", "trustees", "governance", "leadership", "staff", "team", "contact"),
        "role_boost_terms": ("executive director", "ceo", "board chair", "facilities manager", "operations director"),
        "department_boost_terms": ("facilities", "operations", "administrative office"),
        "strategy_summary": "Favor board, executive leadership, staff directories, and nonprofit public-record traces.",
    },
    "public_institution": {
        "label": "Public institution / civic entity",
        "query_variants": (
            "facilities director",
            "maintenance supervisor",
            "operations director",
            "capital projects",
            "public works",
            "administration",
            "leadership",
            "contact",
        ),
        "link_hints": ("departments", "administration", "leadership", "staff", "facilities", "projects", "contact"),
        "role_boost_terms": ("facilities director", "public works", "maintenance supervisor", "operations director", "administrator"),
        "department_boost_terms": ("facilities", "maintenance", "operations", "administration"),
        "strategy_summary": "Favor facilities, maintenance, administration, and capital-project signals over board-style outreach.",
    },
    "contractor_builder": {
        "label": "Contractor / builder / trades business",
        "query_variants": (
            "owner",
            "president",
            "principal",
            "project manager",
            "operations manager",
            "estimating",
            "estimator",
            "service manager",
            "office manager",
            "leadership",
            "contact",
        ),
        "link_hints": ("about", "team", "leadership", "projects", "services", "contact", "contact-us"),
        "role_boost_terms": (
            "owner",
            "president",
            "principal",
            "project manager",
            "operations manager",
            "service manager",
            "estimator",
            "estimating",
            "office manager",
            "office administrator",
        ),
        "department_boost_terms": ("operations", "construction", "service", "estimating", "project management", "administrative office"),
        "strategy_summary": "Favor owners, presidents, project/service/estimating leaders, and office routing over board/governance sources.",
    },
    "retail_multi_site": {
        "label": "Retail / multi-site operator",
        "query_variants": (
            "facilities manager",
            "regional manager",
            "store development",
            "construction manager",
            "real estate",
            "operations manager",
            "franchise manager",
            "franchisee",
            "grand opening",
            "expansion",
            "contact",
        ),
        "link_hints": ("locations", "about", "leadership", "real-estate", "contact", "team"),
        "role_boost_terms": ("facilities manager", "regional manager", "construction manager", "real estate", "operations manager", "franchise manager", "franchisee", "operator"),
        "department_boost_terms": ("facilities", "operations", "capital projects", "development"),
        "strategy_summary": "Favor franchise operators, regional operations, store development, and real-estate/construction routes over brand-level leadership.",
    },
    "private_company": {
        "label": "Private company / LLC / corporation",
        "query_variants": (
            "leadership",
            "team",
            "contact",
            "operations manager",
            "facilities manager",
            "maintenance manager",
            "office manager",
        ),
        "link_hints": ("about", "leadership", "team", "contact", "staff"),
        "role_boost_terms": ("operations manager", "facilities manager", "maintenance manager", "office manager", "director"),
        "department_boost_terms": ("facilities", "maintenance", "operations", "administrative office"),
        "strategy_summary": "Favor operations, facilities, maintenance, and office-routing signals from company-controlled public sources.",
    },
}

DEFAULT_PROFILE_KEY = "private_company"


class LeadInvestigationError(RuntimeError):
    pass


@dataclass
class FetchedPage:
    url: str
    title: str
    site_name: str
    text: str
    links: list[str]
    source_type: str = "company_website"


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    source_type: str


class _SimpleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value.strip())

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.text_parts.append(text)


class _DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self._capture_title = False
        self._capture_snippet = False
        self._current_url = ""
        self._current_title_parts: list[str] = []
        self._current_snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs}
        class_value = (attrs_dict.get("class") or "").lower()
        if tag.lower() == "a" and "result__a" in class_value:
            href = attrs_dict.get("href") or ""
            self._current_url = _normalize_search_result_url(href)
            self._current_title_parts = []
            self._current_snippet_parts = []
            self._capture_title = True
            self._capture_snippet = False
        elif tag.lower() in {"a", "div", "span"} and "result__snippet" in class_value:
            self._current_snippet_parts = []
            self._capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name == "a" and self._capture_title:
            self._capture_title = False
        elif self._capture_snippet and tag_name in {"a", "div", "span"}:
            self._capture_snippet = False
            if self._current_url and self._current_title_parts:
                title = re.sub(r"\s+", " ", " ".join(self._current_title_parts)).strip()
                snippet = re.sub(r"\s+", " ", " ".join(self._current_snippet_parts)).strip()
                if title and self._current_url:
                    source_type = _classify_public_source(self._current_url)
                    self.results.append(
                        SearchResult(
                            url=self._current_url,
                            title=title,
                            snippet=snippet,
                            source_type=source_type,
                        )
                    )
                self._current_url = ""
                self._current_title_parts = []
                self._current_snippet_parts = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._capture_title:
            self._current_title_parts.append(text)
        elif self._capture_snippet:
            self._current_snippet_parts.append(text)


def _normalize_url(value: str) -> str:
    if not value:
        return ""
    candidate = value.strip()
    if not candidate:
        return ""
    if not re.match(r"^[a-z]+://", candidate, re.I):
        candidate = f"https://{candidate}"
    parsed = parse.urlparse(candidate)
    if not parsed.netloc:
        raise LeadInvestigationError("Provided website is not a valid public URL.")
    return parse.urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path or "/",
            "",
            "",
            "",
        )
    )


def _normalize_search_result_url(value: str) -> str:
    if not value:
        return ""
    candidate = html_unescape_url(value.strip())
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    parsed = parse.urlparse(candidate)
    if "duckduckgo.com" in parsed.netloc.lower():
        query = parse.parse_qs(parsed.query)
        if "uddg" in query and query["uddg"]:
            candidate = query["uddg"][0]
            parsed = parse.urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))


def html_unescape_url(value: str) -> str:
    return unescape(value).replace("&amp;", "&")


def _fetch_url(url: str) -> str:
    req = request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                raise LeadInvestigationError(f"Public page is not HTML: {url}")
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except error.HTTPError as exc:
        raise LeadInvestigationError(f"Public page returned HTTP {exc.code}: {url}") from exc
    except error.URLError as exc:
        raise LeadInvestigationError(f"Unable to reach public page: {url}") from exc


def _fetch_optional_url(url: str) -> str:
    try:
        return _fetch_url(url)
    except LeadInvestigationError:
        return ""


def _clean_text(raw_text: str) -> str:
    text = unescape(raw_text)
    text = re.sub(r"(?is)<script.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_title(html: str) -> str:
    match = TITLE_RE.search(html)
    if not match:
        return ""
    return re.sub(r"\s+", " ", unescape(match.group(1))).strip()


def _extract_site_name(html: str) -> str:
    match = SITE_NAME_RE.search(html)
    if match:
        return re.sub(r"\s+", " ", unescape(match.group(1))).strip()
    return ""


def _parse_page(url: str, html: str) -> FetchedPage:
    parser = _SimpleHTMLParser()
    parser.feed(html)
    text = _clean_text(" ".join(parser.text_parts))
    links = [parse.urljoin(url, href) for href in parser.links]
    return FetchedPage(
        url=url,
        title=_extract_title(html),
        site_name=_extract_site_name(html),
        text=text,
        links=links,
        source_type=_classify_public_source(url),
    )


def _profile_config(profile_key: str) -> dict:
    return ENTITY_PROFILES.get(profile_key, ENTITY_PROFILES[DEFAULT_PROFILE_KEY])


def _detect_entity_profile(
    *,
    target_name: str,
    website: str,
    lead_context: str,
    combined_text: str = "",
) -> str:
    primary_evidence = " ".join(
        part
        for part in [target_name, website, lead_context]
        if part
    ).lower()
    secondary_evidence = (combined_text or "").lower()

    scores = {
        "nonprofit": 0,
        "public_institution": 0,
        "contractor_builder": 0,
        "retail_multi_site": 0,
        DEFAULT_PROFILE_KEY: 1,
    }

    token_groups = {
        "nonprofit": NONPROFIT_TOKENS,
        "public_institution": PUBLIC_INSTITUTION_TOKENS,
        "contractor_builder": CONTRACTOR_TOKENS,
        "retail_multi_site": RETAIL_TOKENS,
    }

    for profile_key, tokens in token_groups.items():
        for token in tokens:
            if token in primary_evidence:
                scores[profile_key] += 4
            elif token in secondary_evidence:
                scores[profile_key] += 1

    if re.search(r"\b(llc|inc|corp|corporation|co\.)\b", primary_evidence):
        scores[DEFAULT_PROFILE_KEY] += 3

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_key, best_score = ranked[0]
    if best_score <= 1:
        return DEFAULT_PROFILE_KEY
    return best_key


def _build_search_queries(
    target_name: str,
    city_state: str,
    website: str,
    lead_context: str,
    profile_key: str,
) -> list[str]:
    base = " ".join(part for part in [target_name, city_state] if part).strip()
    if not base:
        return []
    profile = _profile_config(profile_key)
    queries: list[str] = []
    for variant in profile.get("query_variants", QUERY_VARIANTS):
        queries.append(f"{base} {variant}")
    if website:
        host = parse.urlparse(website).netloc.lower().replace("www.", "")
        if host:
            for variant in profile.get("query_variants", QUERY_VARIANTS)[:5]:
                queries.append(f"site:{host} {target_name} {variant}")
    if lead_context and "rebate" in lead_context.lower():
        queries.append(f"{base} facilities manager rebate")
    queries.extend(
        [
            f"{base} grand opening",
            f"{base} franchisee",
            f"{base} llc",
            f"{base} operator",
            f"{base} expansion",
        ]
    )
    if profile_key == "nonprofit":
        queries.extend(
            [
                f"{base} board of directors",
                f"{base} executive director",
                f"{base} form 990",
            ]
        )
    if profile_key == "public_institution":
        queries.extend(
            [
                f"{base} facilities director",
                f"{base} public works",
                f"{base} capital projects",
            ]
        )
    if profile_key == "contractor_builder":
        queries.extend(
            [
                f"{base} owner",
                f"{base} project manager",
                f"{base} estimating",
            ]
        )
    if profile_key == "retail_multi_site":
        queries.extend(
            [
                f"{base} regional manager",
                f"{base} store development",
                f"{base} facilities manager",
                f"{base} franchise manager",
            ]
        )
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = query.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped[:8]

def _state_scope(city_state: str) -> str:
    parts = [part.strip() for part in (city_state or "").split(",") if part.strip()]
    return parts[-1] if parts else city_state.strip()


def _entity_person_queries(entity_name: str, city_state: str) -> list[str]:
    state = _state_scope(city_state)
    if not entity_name.strip() or not state:
        return []
    return [
        f"{entity_name} {state} Ryan Schneider",
        f"{entity_name} {state} franchise manager",
        f"{entity_name} {state} operator",
        f"{entity_name} {state} grand opening",
        f"{entity_name} {state} expansion",
        f"{entity_name} {state} Kalispell",
    ]
def _classify_public_source(url: str) -> str:
    host = parse.urlparse(url).netloc.lower()
    if any(token in host for token in ("irs.gov", "guidestar", "propublica")):
        return "nonprofit_record"
    if any(token in host for token in ("sec.gov", "sam.gov")):
        return "official_registry"
    if any(token in host for token in ("opencorporates", "sos", "bizapedia")):
        return "business_registry"
    if any(token in host for token in ("linkedin.com", "zoominfo.com", "rocketreach.co")):
        return "public_profile"
    if any(token in host for token in ("facebook.com", "instagram.com", "x.com", "twitter.com", "tiktok.com")):
        return "public_social"
    if any(token in host for token in LOCAL_PRESS_HINTS):
        return "local_press"
    return "company_website"


def _fetch_public_search_results(
    target_name: str,
    city_state: str,
    website: str,
    lead_context: str,
    profile_key: str,
) -> list[SearchResult]:
    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    for query in _build_search_queries(target_name, city_state, website, lead_context, profile_key):
        search_url = "https://html.duckduckgo.com/html/?q=" + parse.quote_plus(query)
        html = _fetch_optional_url(search_url)
        if not html:
            continue
        parser = _DuckDuckGoHTMLParser()
        parser.feed(html)
        for result in parser.results:
            if not result.url or result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            results.append(result)
    ranked = sorted(
        results,
        key=lambda item: _score_search_result_for_investigation(
            item,
            target_name=target_name,
            city_state=city_state,
            lead_context=lead_context,
            profile_key=profile_key,
        ),
        reverse=True,
    )
    return ranked[:MAX_SEARCH_RESULTS]


def _pick_relevant_links(base_url: str, links: Iterable[str], profile_key: str, city_state: str = "") -> list[str]:
    base_host = parse.urlparse(base_url).netloc.lower()
    profile = _profile_config(profile_key)
    profile_hints = tuple(profile.get("link_hints", ()))
    location_tokens = _location_tokens("", city_state)
    base_lower = base_url.lower()
    base_is_generic_location_index = any(hint in base_lower for hint in GENERIC_LOCATION_PATH_HINTS)
    chosen: list[str] = []
    seen: set[str] = set()
    secondary_matches: list[str] = []
    for link in links:
        parsed = parse.urlparse(link)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc.lower() != base_host:
            continue
        normalized = parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
        lowered = normalized.lower()
        if lowered in seen:
            continue
        is_location_link = any(hint in lowered for hint in GENERIC_LOCATION_PATH_HINTS)
        if (
            profile_key == "retail_multi_site"
            and base_is_generic_location_index
            and is_location_link
            and location_tokens
            and not any(token in lowered for token in location_tokens)
        ):
            continue
        if any(hint in lowered for hint in profile_hints):
            seen.add(lowered)
            chosen.append(normalized)
        elif any(hint in lowered for hint in CONTACT_PATH_HINTS):
            seen.add(lowered)
            secondary_matches.append(normalized)
        if len(chosen) >= MAX_WEBSITE_PAGES - 1:
            break
    for link in secondary_matches:
        if len(chosen) >= MAX_WEBSITE_PAGES - 1:
            break
        chosen.append(link)
    return chosen


def _extract_emails(text: str) -> list[str]:
    values = []
    for match in EMAIL_RE.findall(text):
        email_value = match.strip().lower().rstrip(".,;:")
        if email_value not in values:
            values.append(email_value)
    return values


def _extract_phones(text: str) -> list[str]:
    values = []
    for match in PHONE_RE.findall(text):
        phone_value = re.sub(r"\s+", " ", match).strip().rstrip(".,;:")
        if phone_value not in values:
            values.append(phone_value)
    return values


def _sentence_chunks(text: str) -> list[str]:
    rough = re.split(r"(?<=[.!?])\s+|\s{2,}", text)
    return [chunk.strip() for chunk in rough if chunk.strip()]


def _normalize_candidate_name(name: str) -> str:
    parts = [part for part in re.split(r"\s+", name.strip()) if part]
    while parts and parts[0].lower().strip(".,:;") in NOISY_NAME_PREFIXES:
        parts.pop(0)
    if len(parts) < 2:
        return ""
    cleaned = " ".join(parts[:3]).strip(" -\u2013\u2014")
    if not re.match(r"^[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){1,2}$", cleaned):
        return ""
    return cleaned


def _normalize_role_text(role: str) -> str:
    role_clean = re.sub(r"\s+", " ", role).strip(" -\u2013\u2014")
    role_clean = re.sub(r"\s+at\s+.+$", "", role_clean, flags=re.I)
    role_clean = re.sub(
        r"\s+[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+)?$",
        "",
        role_clean,
    )
    return role_clean.strip(" -\u2013\u2014")


def _target_tokens(target_name: str) -> set[str]:
    return {
        token.lower()
        for token in re.split(r"[^a-zA-Z0-9]+", target_name or "")
        if len(token.strip()) >= 2
    }


def _location_tokens(address: str, city_state: str) -> set[str]:
    raw = " ".join(part for part in [address, city_state] if part)
    return {
        token.lower()
        for token in re.split(r"[^a-zA-Z0-9]+", raw)
        if len(token.strip()) >= 2
    }


def _extract_operating_entity(text: str) -> str:
    match = ENTITY_NAME_RE.search(text or "")
    return match.group(1).strip() if match else ""


def _score_search_result_for_homepage(
    result: SearchResult,
    target_name: str,
    address: str,
    city_state: str,
    profile_key: str = DEFAULT_PROFILE_KEY,
) -> int:
    url = result.url.lower()
    title = (result.title or "").lower()
    snippet = (result.snippet or "").lower()
    haystack = f"{title} {snippet} {url}"

    score = 0

    if result.source_type == "company_website":
        score += 5
    elif result.source_type in {"business_registry", "official_registry"}:
        score += 2
    elif result.source_type == "local_press":
        score += 1
    else:
        score -= 2

    bad_hosts = (
        "facebook.com",
        "instagram.com",
        "x.com",
        "twitter.com",
        "linkedin.com",
        "zoominfo.com",
        "rocketreach.co",
        "bizapedia.com",
        "opencorporates.com",
        "duckduckgo.com",
        "yelp.com",
        "mapquest.com",
    )
    if any(host in url for host in bad_hosts):
        score -= 4

    if any(path_hint in url for path_hint in ("/locations/", "/location/", "/stores/", "/store/", "/about", "/contact")):
        score += 3

    tokens = _target_tokens(target_name)
    token_hits = sum(1 for token in tokens if token in haystack)
    score += token_hits * 2

    loc_tokens = _location_tokens(address, city_state)
    loc_hits = sum(1 for token in loc_tokens if token in haystack)
    score += min(loc_hits, 3)

    if profile_key == "retail_multi_site":
        operator_hits = sum(1 for token in OPERATOR_SIGNAL_TERMS if token in haystack)
        score += operator_hits * 2
        if result.source_type == "local_press":
            score += 6
        if any(hint in url for hint in GENERIC_LOCATION_PATH_HINTS):
            score -= 5
            if "near you" in haystack or "find a" in haystack:
                score -= 4
        if "mapquest.com" in url:
            score -= 3

    return score


def _score_search_result_for_investigation(
    result: SearchResult,
    *,
    target_name: str,
    city_state: str,
    lead_context: str,
    profile_key: str,
) -> int:
    url = (result.url or "").lower()
    title = (result.title or "").lower()
    snippet = (result.snippet or "").lower()
    haystack = " ".join(part for part in [title, snippet, url, lead_context.lower()] if part)
    score = 0

    if result.source_type == "local_press":
        score += 9
    elif result.source_type == "business_registry":
        score += 6
    elif result.source_type == "official_registry":
        score += 5
    elif result.source_type == "company_website":
        score += 3
    elif result.source_type == "public_profile":
        score += 1
    else:
        score -= 2

    bad_hosts = (
        "facebook.com",
        "instagram.com",
        "x.com",
        "twitter.com",
        "linkedin.com",
        "mapquest.com",
        "yelp.com",
        "duckduckgo.com",
    )
    if any(host in url for host in bad_hosts):
        score -= 5

    target_hits = sum(1 for token in _target_tokens(target_name) if token in haystack)
    score += target_hits * 2

    loc_hits = sum(1 for token in _location_tokens("", city_state) if token in haystack)
    score += min(loc_hits, 3)

    operator_hits = sum(1 for token in OPERATOR_SIGNAL_TERMS if token in haystack)
    score += operator_hits * 3

    if profile_key == "retail_multi_site":
        if result.source_type == "local_press":
            score += 4
        if any(hint in url for hint in GENERIC_LOCATION_PATH_HINTS):
            score -= 4
            if "near you" in haystack or "find a" in haystack:
                score -= 4
        if any(token in haystack for token in ("franchise manager", "franchisee", "operator", "llc", "grand opening", "expansion")):
            score += 5

    return score


def _discover_public_homepage(
    target_name: str,
    address: str,
    city_state: str,
    lead_context: str,
    profile_key: str,
) -> tuple[str, list[SearchResult], list[str]]:
    queries_run = _build_search_queries(target_name, city_state, "", lead_context, profile_key)
    search_results = _fetch_public_search_results(
        target_name=target_name,
        city_state=city_state,
        website="",
        lead_context=lead_context,
        profile_key=profile_key,
    )

    if not search_results:
        raise LeadInvestigationError(
            "FieldOps could not discover usable public-source results from business-name-first search."
        )

    ranked = sorted(
        search_results,
        key=lambda item: _score_search_result_for_homepage(item, target_name, address, city_state, profile_key),
        reverse=True,
    )

    best = ranked[0]
    return _normalize_url(best.url), ranked, queries_run


def _extract_role_candidates_from_text(
    text: str,
    desired_contact_type: str,
    *,
    source_url: str,
    source_type: str,
) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()
    desired_tokens = {
        token.lower()
        for token in re.split(r"[^a-zA-Z]+", desired_contact_type or "")
        if token.strip()
    }
    if source_type == "job_board":
        return []
    for chunk in _sentence_chunks(text):
        lowered = chunk.lower()
        if not any(keyword in lowered for keyword in ROLE_KEYWORDS):
            continue
        for name, role in NAME_ROLE_RE.findall(chunk):
            name_clean = _normalize_candidate_name(name)
            role_clean = _normalize_role_text(role)
            if not name_clean or not role_clean:
                continue
            if not any(hint in role_clean.lower() for hint in TITLE_HINTS):
                continue
            key = (name_clean, role_clean.lower())
            if key in seen:
                continue
            seen.add(key)
            confidence = "Medium"
            reason = "Named on a public page with a role/title."
            if source_type == "local_press":
                confidence = "High"
                reason = "Named in local public coverage tied to the target business or rollout."
            if desired_tokens and any(token in role_clean.lower() for token in desired_tokens):
                confidence = "High"
                reason = "Named on a public page with a role matching the requested contact type."
            candidates.append(
                {
                    "full_name": name_clean,
                    "role": role_clean,
                    "confidence": confidence,
                    "finding_type": "confirmed_named_contact",
                    "why_relevant": reason,
                    "source_url": source_url,
                    "source_type": source_type,
                    "source_excerpt": chunk[:240],
                }
            )
        for role, name in ROLE_NAME_RE.findall(chunk):
            role_clean = _normalize_role_text(role)
            name_clean = _normalize_candidate_name(name)
            if not name_clean or not role_clean:
                continue
            key = (name_clean, role_clean.lower())
            if key in seen:
                continue
            seen.add(key)
            confidence = "Medium"
            reason = "Named on a public page with a public leadership title."
            if source_type == "local_press":
                confidence = "High"
                reason = "Named in local public coverage with an operational title."
            if desired_tokens and any(token in role_clean.lower() for token in desired_tokens):
                confidence = "High"
                reason = "Named on a public page with a title aligned to the requested contact type."
            candidates.append(
                {
                    "full_name": name_clean,
                    "role": role_clean,
                    "confidence": confidence,
                    "finding_type": "confirmed_named_contact",
                    "why_relevant": reason,
                    "source_url": source_url,
                    "source_type": source_type,
                    "source_excerpt": chunk[:240],
                }
            )
    return candidates[:8]


def _extract_department_routes(
    text: str,
    desired_contact_type: str,
    *,
    source_url: str,
    source_type: str,
    profile_key: str,
) -> list[dict]:
    candidates: list[dict] = []
    lowered = text.lower()
    profile = _profile_config(profile_key)
    desired_tokens = {
        token.lower()
        for token in re.split(r"[^a-zA-Z]+", desired_contact_type or "")
        if token.strip()
    }
    for keyword, label in DEPARTMENT_HINTS:
        if keyword not in lowered:
            continue
        confidence = "Medium"
        reason = f"Public page text references {label.lower()}."
        if desired_tokens and any(token in keyword for token in desired_tokens):
            confidence = "High"
            reason = f"Public page text references {label.lower()}, which aligns to the requested contact type."
        elif any(term in label.lower() for term in profile.get("department_boost_terms", ())):
            confidence = "High"
            reason = f"Public page text references {label.lower()}, which aligns to the {profile['label'].lower()} strategy."
        candidates.append(
            {
                "department": label,
                "confidence": confidence,
                "finding_type": "inferred_department_route",
                "why_relevant": reason,
                "source_url": source_url,
                "source_type": source_type,
            }
        )
    deduped: list[dict] = []
    seen: set[str] = set()
    for item in candidates:
        key = item["department"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:5]


def _dedupe_role_candidates(candidates: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = (
            (item.get("full_name") or "").strip().lower(),
            (item.get("role") or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:8]


def _dedupe_department_routes(routes: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for item in routes:
        key = (item.get("department") or "").strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:5]


def _supports_for_page(page: FetchedPage) -> str:
    lowered = page.url.lower()
    if page.source_type == "nonprofit_record":
        return "Public nonprofit leadership or board record"
    if page.source_type == "business_registry":
        return "Public business registration signal"
    if page.source_type == "official_registry":
        return "Official public registry signal"
    if page.source_type == "local_press":
        return "Local press or expansion coverage"
    if page.source_type == "public_social":
        return "Public social signal"
    if page.source_type == "public_profile":
        return "Public professional profile"
    if "services" in lowered:
        return "Public services or trade-scope information"
    if "projects" in lowered:
        return "Public project or portfolio information"
    if "board" in lowered or "trustee" in lowered or "governance" in lowered:
        return "Board or governance information"
    if "leadership" in lowered or "staff" in lowered or "team" in lowered or "directory" in lowered:
        return "Staff or leadership information"
    if "contact" in lowered or "about" in lowered:
        return "Public contact or organization information"
    return "Public company/contact information"


def _rank_contact_candidate(candidate: dict, desired_contact_type: str, profile_key: str) -> int:
    score = 0
    confidence = (candidate.get("confidence") or "").lower()
    role = (candidate.get("role") or "").lower()
    source_type = (candidate.get("source_type") or "").lower()
    profile = _profile_config(profile_key)
    if confidence == "high":
        score += 5
    elif confidence == "medium":
        score += 3
    else:
        score += 1
    if source_type in {"company_website", "official_registry", "nonprofit_record", "local_press", "public_profile"}:
        score += 2
    desired_tokens = {
        token.lower()
        for token in re.split(r"[^a-zA-Z]+", desired_contact_type or "")
        if token.strip()
    }
    if desired_tokens and any(token in role for token in desired_tokens):
        score += 4
    if any(token in role for token in ("facilities", "operations", "maintenance", "engineering", "director", "manager", "franchise", "operator", "development")):
        score += 2
    if any(token in role for token in ("board chair", "board president", "executive director", "ceo")):
        score += 1
    if any(token in role for token in profile.get("role_boost_terms", ())):
        score += 4
    if profile_key == "contractor_builder" and source_type == "business_registry" and any(
        token in role for token in ("owner", "president", "principal")
    ):
        score += 3
    if source_type == "local_press" and any(token in role for token in ("franchise", "operator", "owner", "manager", "developer")):
        score += 4
    return score


def _choose_best_contact(candidates: list[dict], desired_contact_type: str, profile_key: str) -> dict | None:
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda item: (
            _rank_contact_candidate(item, desired_contact_type, profile_key),
            item.get("full_name", ""),
        ),
        reverse=True,
    )
    return ranked[0]


def _search_result_to_page(result: SearchResult) -> FetchedPage:
    text = " ".join(part for part in [result.title, result.snippet] if part).strip()
    return FetchedPage(
        url=result.url,
        title=result.title,
        site_name="",
        text=text,
        links=[],
        source_type=result.source_type,
    )


def investigate_public_lead(
    *,
    target_name: str,
    website: str = "",
    address: str = "",
    city_state: str = "",
    known_person: str = "",
    known_phone: str = "",
    known_email: str = "",
    desired_contact_type: str = "",
    lead_context: str = "",
) -> dict:
    if not target_name.strip():
        raise LeadInvestigationError(
            "Lead investigation requires a target name or business name."
        )

    discovered_search_results: list[SearchResult] = []
    query_trace: list[str] = []

    initial_profile_key = _detect_entity_profile(
        target_name=target_name,
        website=website or "",
        lead_context=lead_context,
    )

    if website.strip():
        base_url = _normalize_url(website)
        query_trace = _build_search_queries(target_name, city_state, website, lead_context, initial_profile_key)
    else:
        base_url, discovered_search_results, query_trace = _discover_public_homepage(
            target_name=target_name,
            address=address,
            city_state=city_state,
            lead_context=lead_context,
            profile_key=initial_profile_key,
        )

    pages: list[FetchedPage] = []
    home_html = _fetch_optional_url(base_url)
    if home_html:
        pages.append(_parse_page(base_url, home_html))
        for link in _pick_relevant_links(base_url, pages[0].links, initial_profile_key, city_state):
            html = _fetch_optional_url(link)
            if not html:
                continue
            pages.append(_parse_page(link, html))
    else:
        pages.append(
            FetchedPage(
                url=base_url,
                title="",
                site_name="",
                text="",
                links=[],
                source_type=_classify_public_source(base_url),
            )
        )

    search_results = discovered_search_results or _fetch_public_search_results(
        target_name=target_name,
        city_state=city_state,
        website=base_url,
        lead_context=lead_context,
        profile_key=initial_profile_key,
    )
    for result in search_results:
        pages.append(_search_result_to_page(result))
        if len(pages) >= (MAX_WEBSITE_PAGES + MAX_SEARCH_RESULTS + 2):
            break

    combined_text = "\n".join(page.text for page in pages if page.text)
    if not combined_text:
        raise LeadInvestigationError(
            "FieldOps reached public-source results but could not extract usable public text."
        )

    operating_entity = _extract_operating_entity(combined_text)
    if operating_entity and operating_entity.lower() not in target_name.lower():
        entity_queries = (
            _build_search_queries(
                operating_entity,
                city_state,
                "",
                lead_context,
                initial_profile_key,
            )
            + _entity_person_queries(operating_entity, city_state)
        )
        for query in entity_queries:
            if query not in query_trace:
                query_trace.append(query)
        entity_results = _fetch_public_search_results(
            target_name=operating_entity,
            city_state=city_state,
            website="",
            lead_context=lead_context,
            profile_key=initial_profile_key,
        )
        existing_urls = {page.url for page in pages}
        for result in entity_results:
            if result.url in existing_urls:
                continue
            pages.append(_search_result_to_page(result))
            existing_urls.add(result.url)
            if len(pages) >= (MAX_WEBSITE_PAGES + (MAX_SEARCH_RESULTS * 2) + 2):
                break
        combined_text = "\n".join(page.text for page in pages if page.text)

    profile_key = _detect_entity_profile(
        target_name=target_name,
        website=base_url,
        lead_context=lead_context,
        combined_text=combined_text,
    )
    profile = _profile_config(profile_key)

    emails = _extract_emails(combined_text)
    phones = _extract_phones(combined_text)
    all_candidates: list[dict] = []
    all_department_routes: list[dict] = []
    for page in pages:
        if not page.text:
            continue
        all_candidates.extend(
            _extract_role_candidates_from_text(
                page.text,
                desired_contact_type,
                source_url=page.url,
                source_type=page.source_type,
            )
        )
        all_department_routes.extend(
            _extract_department_routes(
                page.text,
                desired_contact_type,
                source_url=page.url,
                source_type=page.source_type,
                profile_key=profile_key,
            )
        )
    candidates = _dedupe_role_candidates(all_candidates)
    department_routes = _dedupe_department_routes(all_department_routes)

    entity_name = (
        operating_entity
        or next((page.site_name for page in pages if page.site_name), "")
        or next((page.title.split("|")[0].split("-")[0].strip() for page in pages if page.title.strip()), "")
        or target_name
    )
    nonprofit_signals = any(token in f"{target_name} {entity_name} {lead_context}".lower() for token in NONPROFIT_TOKENS) or any(
        page.source_type == "nonprofit_record" for page in pages
    )
    source_trail = [
        {
            "source": page.url,
            "source_type": page.source_type,
            "source_date": "",
            "supports": _supports_for_page(page),
        }
        for page in pages
        if page.url
    ]

    contact_ladder = []
    if known_person:
        contact_ladder.append(
            {
                "label": "Known person clue",
                "value": known_person,
                "confidence": "Medium",
            }
        )
    if known_email:
        contact_ladder.append(
            {"label": "Known email clue", "value": known_email, "confidence": "High"}
        )
    if known_phone:
        contact_ladder.append(
            {"label": "Known phone clue", "value": known_phone, "confidence": "High"}
        )
    for email_value in emails[:4]:
        contact_ladder.append(
            {"label": "Public email", "value": email_value, "confidence": "High"}
        )
    for phone_value in phones[:3]:
        contact_ladder.append(
            {"label": "Public phone", "value": phone_value, "confidence": "High"}
        )
    for route in department_routes[:3]:
        contact_ladder.append(
            {
                "label": "Likely department route",
                "value": route["department"],
                "confidence": route["confidence"],
            }
        )
    contact_ladder.append(
        {
            "label": "Primary public source path",
            "value": base_url,
            "confidence": "High",
        }
    )

    recommendation = "Pursue with caution"
    if candidates and (emails or phones or department_routes):
        recommendation = "Pursue"
    elif not candidates and not emails and not phones and not department_routes:
        recommendation = "Insufficient evidence"

    evidence_summary = (
        f"Reviewed {len(pages)} public source(s) for {entity_name or target_name}. "
        f"Found {len(candidates)} decision-maker candidate(s), "
        f"{len(emails)} public email(s), {len(phones)} public phone number(s), "
        f"and {len(department_routes)} likely routing department(s)."
    )
    best_contact = _choose_best_contact(candidates, desired_contact_type, profile_key)
    entity_type = {
        "nonprofit": "public_nonprofit_match",
        "public_institution": "public_institution_match",
        "contractor_builder": "contractor_builder_match",
        "retail_multi_site": "retail_multi_site_match",
        "private_company": "private_company_match",
    }.get(profile_key, "public_source_match")

    return {
        "verified_entity": {
            "name": entity_name or target_name,
            "website": base_url,
            "address": address,
            "city_state": city_state,
            "entity_type": entity_type,
        },
        "lead_relevance": {
            "reason": lead_context or "No L2 context provided.",
            "summary": evidence_summary,
            "viability": recommendation,
        },
        "investigation_profile": {
            "key": profile_key,
            "label": profile["label"],
            "strategy_summary": profile["strategy_summary"],
        },
        "best_contact": best_contact,
        "decision_maker_map": candidates,
        "department_routes": department_routes,
        "contact_ladder": contact_ladder,
        "source_trail": source_trail,
        "recommendation": recommendation,
        "reviewed_pages": [page.url for page in pages if page.url],
        "nonprofit_signals": nonprofit_signals,
        "query_trace": query_trace,
        "search_result_trace": [
            {
                "url": result.url,
                "title": result.title,
                "snippet": result.snippet,
                "source_type": result.source_type,
            }
            for result in search_results[:MAX_SEARCH_RESULTS]
        ],
        "operating_entity": operating_entity,
    }
