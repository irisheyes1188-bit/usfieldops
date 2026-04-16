from __future__ import annotations

import hashlib
import logging
import re
import time
import urllib.parse
from typing import Any

try:
    import requests as _requests
except ImportError:  # pragma: no cover - exercised indirectly via runtime fallback
    _requests = None

try:
    from bs4 import BeautifulSoup as _BeautifulSoup
except ImportError:  # pragma: no cover - exercised indirectly via runtime fallback
    _BeautifulSoup = None


logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; FieldOpsResearchSkill/1.0; +https://usfieldops.com)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_REQUEST_TIMEOUT = 10
_FETCH_DELAY_SECONDS = 0.35
_MAX_QUERY_COUNT = 4
_MAX_RESULTS_PER_QUERY = 6
_DEFAULT_MAX_SOURCES = 6
_MAX_FINDINGS = 12
_MIN_PAGE_TEXT_LENGTH = 200
_MAX_EXCERPT_LENGTH = 420
_MAX_RUN_SECONDS = 28

_SKIP_DOMAIN_FRAGMENTS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "pinterest.com",
    "reddit.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "youtube.com",
}
_TRUST_DOMAIN_FRAGMENTS = {
    ".edu",
    ".gov",
    "energy.gov",
    "epa.gov",
    "irs.gov",
    "mt.gov",
    "ncat.org",
    "nrel.gov",
    "state.mt.us",
    "usda.gov",
}
_STOP_WORDS = {
    "a",
    "about",
    "all",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "get",
    "had",
    "has",
    "have",
    "how",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "look",
    "may",
    "might",
    "must",
    "not",
    "of",
    "on",
    "or",
    "please",
    "provide",
    "research",
    "should",
    "so",
    "that",
    "the",
    "their",
    "them",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "use",
    "want",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
}
_NUMERIC_PATTERNS = (
    r"[\$€£]?\d[\d,\.]*\s*(?:percent|%|million|billion|thousand|acres?|gallons?|tons?|lb|kg|btu|kwh|mw|\$/gal)",
    r"\d+[\-–]\d+\s*(?:percent|%|years?|months?|days?|gallons?|acres?)",
    r"\d[\d,\.]*\s*(?:iecc|irc|reap|seer|hspf|afue|ach50)\b",
)
_DOMAIN_HINTS = (
    "biodiesel",
    "biofuel",
    "code",
    "efficiency",
    "feasibility",
    "grant",
    "heat pump",
    "hemp",
    "hvac",
    "iecc",
    "incentive",
    "montana",
    "ncat",
    "nrel",
    "reap",
    "rebate",
    "tribal",
    "utility",
    "weatherization",
)


class ResearchSkillError(RuntimeError):
    def __init__(self, message: str, error_type: str = "research_error") -> None:
        super().__init__(message)
        self.error_type = error_type


def run_research_skill(
    title: str,
    objective: str,
    lane: str = "General Ops",
    scope: str = "",
    max_sources: int = _DEFAULT_MAX_SOURCES,
) -> dict[str, Any]:
    _ensure_dependencies()

    clean_title = (title or "").strip()
    clean_objective = (objective or "").strip()
    if not clean_title and not clean_objective:
        raise ResearchSkillError(
            "Research skill needs a mission title or objective to search from.",
            error_type="validation_error",
        )

    deadline = time.monotonic() + _MAX_RUN_SECONDS
    queries = _build_queries(clean_title, clean_objective, scope)
    candidates: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    search_errors: list[str] = []

    for query in queries:
        if time.monotonic() >= deadline:
            break
        try:
            for result in _ddg_search(query):
                normalized = _normalise_url(result["url"])
                if not normalized or normalized in seen_urls or _skip_url(result["url"]):
                    continue
                seen_urls.add(normalized)
                candidates.append(result)
        except Exception as exc:  # pragma: no cover - network variance
            search_errors.append(f"{query}: {exc}")
            logger.warning("[research_skill] search failed for %s: %s", query, exc)

    if not candidates:
        detail = (
            "DuckDuckGo search returned no usable results."
            if not search_errors
            else " ; ".join(search_errors[:3])
        )
        raise ResearchSkillError(detail, error_type="retrieval_error")

    sources: list[dict[str, Any]] = []
    for candidate in candidates:
        if len(sources) >= max(1, min(int(max_sources or _DEFAULT_MAX_SOURCES), 10)):
            break
        if time.monotonic() >= deadline:
            break
        page = _fetch_page(candidate["url"])
        if not page:
            continue
        relevance = _score_relevance(page["text"], clean_title, clean_objective)
        if relevance < 0.08:
            continue
        sources.append(
            {
                "url": candidate["url"],
                "title": page["page_title"] or candidate.get("title", ""),
                "domain": _domain(candidate["url"]),
                "excerpt": _extract_excerpt(page["text"], clean_title, clean_objective),
                "relevance_score": round(relevance, 3),
                "word_count": len(page["text"].split()),
            }
        )
        time.sleep(_FETCH_DELAY_SECONDS)

    if not sources:
        raise ResearchSkillError(
            "Search found URLs, but FieldOps could not extract enough usable page content from them.",
            error_type="retrieval_error",
        )

    sources.sort(key=lambda item: item["relevance_score"], reverse=True)
    findings = _extract_findings(sources, clean_title, clean_objective)
    confidence = _assess_confidence(sources, findings)
    brief, summary = _build_brief(
        title=clean_title or clean_objective[:120],
        objective=clean_objective,
        lane=lane,
        scope=scope,
        confidence=confidence,
        findings=findings,
        sources=sources,
    )

    return {
        "brief": brief,
        "summary": summary,
        "confidence": confidence,
        "findings": findings,
        "sources": sources,
        "queries_run": queries,
        "source_count": len(sources),
    }


def _ensure_dependencies() -> None:
    missing: list[str] = []
    if _requests is None:
        missing.append("requests")
    if _BeautifulSoup is None:
        missing.append("beautifulsoup4")
    if missing:
        raise ResearchSkillError(
            "Missing backend dependencies: " + ", ".join(missing),
            error_type="dependency_error",
        )


def _build_queries(title: str, objective: str, scope: str) -> list[str]:
    scope_tag = (scope or "").split(",")[0].strip()
    phrases = _key_phrases(" ".join(filter(None, [title, objective])), max_terms=8)
    queries: list[str] = []

    if title:
        queries.append(" ".join(filter(None, [title, scope_tag])).strip())
    if phrases:
        queries.append(" ".join(phrases[:4]).strip())
    domain_hits = [hint for hint in _DOMAIN_HINTS if hint.lower() in f"{title} {objective}".lower()]
    if title and domain_hits:
        queries.append(f"{title} {domain_hits[0]}")
    if scope_tag and phrases:
        queries.append(f"{' '.join(phrases[:3])} {scope_tag}")

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        clean_query = re.sub(r"\s+", " ", query).strip()
        if clean_query and clean_query not in seen:
            seen.add(clean_query)
            deduped.append(clean_query)
    if not deduped:
        fallback = (title or objective or "general research").strip()
        deduped.append(fallback[:120])
    return deduped[:_MAX_QUERY_COUNT]


def _key_phrases(text: str, max_terms: int = 8) -> list[str]:
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9\-]{2,}\b", text or "")
    results: list[str] = []
    seen: set[str] = set()
    for word in words:
        lowered = word.lower()
        if lowered in _STOP_WORDS or lowered in seen:
            continue
        seen.add(lowered)
        results.append(lowered)
        if len(results) >= max_terms:
            break
    return results


def _ddg_search(query: str) -> list[dict[str, str]]:
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}&kl=us-en"
    response = _requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = _BeautifulSoup(response.text, "html.parser")
    results: list[dict[str, str]] = []

    for node in soup.select(".result"):
        link = node.select_one(".result__a")
        if not link:
            continue
        snippet = node.select_one(".result__snippet")
        real_url = _unwrap_ddg_url(link.get("href", ""))
        if not real_url:
            continue
        results.append(
            {
                "url": real_url,
                "title": link.get_text(" ", strip=True),
                "snippet": snippet.get_text(" ", strip=True) if snippet else "",
            }
        )
        if len(results) >= _MAX_RESULTS_PER_QUERY:
            break
    return results


def _unwrap_ddg_url(href: str) -> str:
    if not href:
        return ""
    if "uddg=" in href:
        full = "https:" + href if href.startswith("//") else href
        query = urllib.parse.urlparse(full).query
        target = urllib.parse.parse_qs(query).get("uddg", [""])[0]
        return urllib.parse.unquote(target)
    return href if href.startswith("http") else ""


def _fetch_page(url: str) -> dict[str, str] | None:
    try:
        response = _requests.get(
            url,
            headers=_HEADERS,
            timeout=_REQUEST_TIMEOUT,
            allow_redirects=True,
        )
    except Exception as exc:  # pragma: no cover - network variance
        logger.debug("[research_skill] fetch failed for %s: %s", url, exc)
        return None
    if response.status_code != 200:
        return None
    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        return None

    soup = _BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "iframe"]):
        tag.decompose()

    body = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=re.compile(r"content|main|article", re.I))
        or soup.find(class_=re.compile(r"content|article|post|body", re.I))
        or soup.find("body")
    )
    if not body:
        return None

    text = re.sub(r"\s+", " ", body.get_text(" ", strip=True)).strip()
    if len(text) < _MIN_PAGE_TEXT_LENGTH:
        return None
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return {"text": text, "page_title": page_title}


def _extract_excerpt(text: str, title: str, objective: str) -> str:
    keywords = _key_phrases(" ".join(filter(None, [title, objective])), max_terms=8)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    scored: list[tuple[int, str]] = []
    for sentence in sentences:
        clean = sentence.strip()
        if len(clean) < 40:
            continue
        hits = sum(1 for keyword in keywords if keyword in clean.lower())
        if hits:
            scored.append((hits, clean))
    scored.sort(key=lambda item: item[0], reverse=True)
    joined = " ".join(sentence for _, sentence in scored[:4]) if scored else text
    clipped = joined[:_MAX_EXCERPT_LENGTH].strip()
    if len(joined) > _MAX_EXCERPT_LENGTH:
        clipped = clipped.rsplit(" ", 1)[0] + "..."
    return clipped


def _score_relevance(text: str, title: str, objective: str) -> float:
    keywords = _key_phrases(" ".join(filter(None, [title, objective])), max_terms=10)
    lowered = text.lower()
    if not keywords:
        return 0.1
    hits = sum(lowered.count(keyword) for keyword in keywords)
    length = max(len(text.split()), 1)
    score = min(hits / length * 10, 1.0)
    if any(fragment in lowered for fragment in ("cookie", "subscribe", "sign up")) and hits < 2:
        score *= 0.6
    return score


def _extract_findings(sources: list[dict[str, Any]], title: str, objective: str) -> list[str]:
    keywords = set(_key_phrases(" ".join(filter(None, [title, objective])), max_terms=8))
    ranked: list[tuple[float, str]] = []
    seen_hashes: set[str] = set()

    for source in sources:
        excerpt = source.get("excerpt", "")
        if not excerpt:
            continue
        for pattern in _NUMERIC_PATTERNS:
            for match in re.finditer(pattern, excerpt, re.I):
                sentence = _nearest_sentence(excerpt, match.start(), match.end())
                if not 35 <= len(sentence) <= 280:
                    continue
                digest = hashlib.md5(sentence[:80].encode("utf-8")).hexdigest()
                if digest in seen_hashes:
                    continue
                seen_hashes.add(digest)
                score = source["relevance_score"] + sum(
                    1 for keyword in keywords if keyword in sentence.lower()
                )
                ranked.append((score, sentence.strip()))

        for sentence in re.split(r"(?<=[.!?])\s+", excerpt):
            clean = sentence.strip()
            if not 45 <= len(clean) <= 280:
                continue
            hits = sum(1 for keyword in keywords if keyword in clean.lower())
            if hits < 2:
                continue
            digest = hashlib.md5(clean[:80].encode("utf-8")).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            ranked.append((source["relevance_score"] + hits, clean))

    ranked.sort(key=lambda item: item[0], reverse=True)
    findings: list[str] = []
    seen_prefixes: set[str] = set()
    for _, sentence in ranked:
        prefix = sentence[:60].lower()
        if prefix in seen_prefixes:
            continue
        seen_prefixes.add(prefix)
        findings.append(sentence)
        if len(findings) >= _MAX_FINDINGS:
            break

    if not findings:
        findings = [
            f"{source['domain']}: {source['excerpt'][:180].strip()}"
            for source in sources[: min(4, len(sources))]
        ]
    return findings


def _nearest_sentence(text: str, start: int, end: int) -> str:
    left = text.rfind(".", 0, start)
    left = 0 if left < 0 else left + 1
    right = text.find(".", end)
    right = len(text) if right < 0 else right + 1
    return text[left:right].strip()


def _assess_confidence(sources: list[dict[str, Any]], findings: list[str]) -> str:
    trusted = sum(
        1
        for source in sources
        if any(fragment in source["domain"] for fragment in _TRUST_DOMAIN_FRAGMENTS)
    )
    if len(sources) >= 5 and len(findings) >= 5 and trusted >= 1:
        return "HIGH"
    if len(sources) >= 3 and len(findings) >= 3:
        return "MEDIUM"
    return "LOW"


def _build_brief(
    title: str,
    objective: str,
    lane: str,
    scope: str,
    confidence: str,
    findings: list[str],
    sources: list[dict[str, Any]],
) -> tuple[str, str]:
    summary = (
        findings[0]
        if findings
        else f"FieldOps retrieved {len(sources)} sources for {title}."
    )
    strengths = _derive_strengths(sources, findings)
    risks = _derive_risks(sources, findings, confidence)
    uncertainties = _derive_uncertainties(sources, findings, confidence)
    bottom_line = _derive_bottom_line(title, confidence, len(sources), len(findings))
    recommendation = _derive_recommendation(confidence, title, findings)
    source_lines = [
        f"- {source['domain']} — {source['url']}"
        for source in sources[: min(6, len(sources))]
    ] or ["- No usable public sources were retained."]

    sections = [
        ("EXECUTIVE SUMMARY", [summary]),
        ("KEY FINDINGS", [f"- {item}" for item in findings[:6]] or ["- No distinct findings were extracted."]),
        ("BENEFITS / STRENGTHS", [f"- {item}" for item in strengths]),
        ("RISKS / DRAWBACKS / CONSTRAINTS", [f"- {item}" for item in risks]),
        ("WHAT REMAINS UNCERTAIN", [f"- {item}" for item in uncertainties]),
        ("BOTTOM-LINE ASSESSMENT", [bottom_line]),
        ("RECOMMENDATION", [recommendation]),
        ("SOURCE BASE", source_lines),
        ("CONFIDENCE LEVEL", [confidence]),
    ]

    header = [
        f"RESEARCH BRIEF: {title}",
        f"Lane: {lane or 'General Ops'}",
        f"Objective: {objective or '[not provided]'}",
    ]
    if scope:
        header.append(f"Scope: {scope}")

    body: list[str] = ["\n".join(header)]
    for section, lines in sections:
        body.append("")
        body.append(f"{section}:")
        body.extend(lines)
    return "\n".join(body).strip(), summary[:400]


def _derive_strengths(sources: list[dict[str, Any]], findings: list[str]) -> list[str]:
    strengths: list[str] = []
    trusted_domains = [source["domain"] for source in sources if any(fragment in source["domain"] for fragment in _TRUST_DOMAIN_FRAGMENTS)]
    if trusted_domains:
        strengths.append(
            "FieldOps found at least one higher-trust source (" + ", ".join(trusted_domains[:3]) + ")."
        )
    if len(sources) >= 4:
        strengths.append("Multiple sources were retrieved, which helps cross-check the topic.")
    if findings:
        strengths.append("The retrieved pages contained enough concrete statements to extract ranked findings.")
    if not strengths:
        strengths.append("FieldOps retrieved at least one directly relevant source.")
    return strengths[:4]


def _derive_risks(sources: list[dict[str, Any]], findings: list[str], confidence: str) -> list[str]:
    risks: list[str] = []
    if confidence == "LOW":
        risks.append("The source set is thin, so this result should be treated as directional rather than decisive.")
    if any(source["word_count"] < 250 for source in sources):
        risks.append("Some retained sources were short pages, which can limit context.")
    if len(findings) < 3:
        risks.append("Few distinct findings were extracted, which raises the chance of blind spots.")
    if not risks:
        risks.append("Public web evidence can still miss paywalled, unpublished, or local operational context.")
    return risks[:4]


def _derive_uncertainties(sources: list[dict[str, Any]], findings: list[str], confidence: str) -> list[str]:
    items: list[str] = []
    if confidence != "HIGH":
        items.append("FieldOps did not find enough corroborating high-trust sources to call this high confidence.")
    if len(sources) < 3:
        items.append("The result may change if additional sources are gathered beyond the first search pass.")
    if not any(re.search(pattern, " ".join(findings), re.I) for pattern in _NUMERIC_PATTERNS):
        items.append("Few quantitative facts were surfaced, so the result leans more qualitative than numeric.")
    if not items:
        items.append("The remaining uncertainty is mainly around local context that may not be published online.")
    return items[:4]


def _derive_bottom_line(title: str, confidence: str, source_count: int, finding_count: int) -> str:
    return (
        f"FieldOps completed a public-web research pass for {title}, retained {source_count} source"
        f"{'s' if source_count != 1 else ''}, extracted {finding_count} ranked finding"
        f"{'s' if finding_count != 1 else ''}, and rates the result {confidence} confidence."
    )


def _derive_recommendation(confidence: str, title: str, findings: list[str]) -> str:
    if confidence == "HIGH":
        return f"Use this brief as a decision-ready starting point for {title}, then validate any operational numbers before acting."
    if findings:
        return f"Treat this as a scoped first pass on {title}; review the cited sources and gather one or two higher-trust confirmations next."
    return f"Run a second research pass for {title} with narrower keywords or a tighter scope before making a decision."


def _domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return url[:40]


def _normalise_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lower() + parsed.path.rstrip("/")
    except Exception:
        return url


def _skip_url(url: str) -> bool:
    domain = _domain(url)
    return any(fragment in domain for fragment in _SKIP_DOMAIN_FRAGMENTS)
