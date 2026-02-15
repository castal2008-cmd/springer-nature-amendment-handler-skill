#!/usr/bin/env python3
"""
verify_citations.py - Verify manuscript citations against PubMed, Semantic Scholar, and CrossRef.

Extracts references from a manuscript file (DOCX or plain text) and verifies each
citation exists in PubMed (via E-utilities), Semantic Scholar (via Academic Graph API),
and CrossRef (via REST API). Includes title similarity scoring to reduce false positives.

Usage:
    python verify_citations.py <manuscript_file> [--output report.json]

Supported input formats: .docx, .txt, .md

Output: JSON report with verification status for each reference, plus a summary.

Dependencies: python-docx (optional, for .docx files)
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import os
from difflib import SequenceMatcher

# Minimum title similarity ratio to accept a match (0.0 - 1.0)
TITLE_SIMILARITY_THRESHOLD = 0.55

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def normalize_title(title):
    """Lowercase, strip punctuation, collapse whitespace for comparison."""
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def title_similarity(a, b):
    """Return similarity ratio between two titles (0.0 - 1.0)."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


# ---------------------------------------------------------------------------
# Reference extraction
# ---------------------------------------------------------------------------

def extract_text_from_docx(filepath):
    """Extract plain text from a DOCX file using python-docx."""
    try:
        from docx import Document
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        sys.exit("Error: python-docx is required for .docx files. Install with: pip install python-docx")


def extract_text(filepath):
    """Return the full text of a manuscript file."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".docx":
        return extract_text_from_docx(filepath)
    else:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def extract_references_section(text):
    """Isolate the References / Bibliography section from manuscript text."""
    patterns = [
        r'(?i)\n\s*references\s*\n',
        r'(?i)\n\s*bibliography\s*\n',
        r'(?i)\n\s*works\s+cited\s*\n',
        r'(?i)\n\s*literature\s+cited\s*\n',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return text[m.end():]
    return ""


def parse_references(ref_text):
    """
    Parse individual references from the references section.
    Handles numbered references (e.g., '1. Author ...') and unnumbered block references.
    Returns a list of raw reference strings.
    """
    refs = []

    # Try numbered references first: "1." or "[1]" or "1)"
    numbered = re.split(r'\n\s*(?:\[?\d+[\].)]\s+)', ref_text)
    numbered = [r.strip() for r in numbered if r.strip() and len(r.strip()) > 15]
    if len(numbered) >= 2:
        return numbered

    # Fall back to paragraph-based splitting
    blocks = re.split(r'\n\s*\n', ref_text)
    for b in blocks:
        b = b.strip()
        if len(b) > 15:
            refs.append(b)
    return refs


def extract_citation_metadata(ref_string):
    """
    Attempt to extract structured metadata from a raw reference string.
    Returns a dict with keys: authors, title, year, journal, doi (any may be None).
    """
    meta = {"raw": ref_string, "authors": None, "title": None, "year": None, "journal": None, "doi": None}

    # DOI
    doi_match = re.search(r'(10\.\d{4,}/[^\s,;]+)', ref_string)
    if doi_match:
        meta["doi"] = doi_match.group(1).rstrip(".")

    # Year
    year_match = re.search(r'[\(\[]?((?:19|20)\d{2})[a-z]?[\)\]]?', ref_string)
    if year_match:
        meta["year"] = year_match.group(1)

    # Title heuristic: text between first period and second period (common in Vancouver/APA)
    parts = ref_string.split(". ")
    if len(parts) >= 3:
        candidate = parts[1].strip()
        if len(candidate) > 10:
            meta["title"] = candidate.rstrip(".")
    elif len(parts) == 2:
        candidate = parts[1].strip()
        if len(candidate) > 10:
            meta["title"] = candidate.rstrip(".")

    # Authors heuristic: text before the first period or year
    if parts:
        meta["authors"] = parts[0].strip()

    return meta


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _http_get_json(url, retries=2):
    """Perform an HTTP GET and return parsed JSON, with retry logic."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ManusAgent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries:
                time.sleep(1.5)
            else:
                return {"error": str(e)}


# ---------------------------------------------------------------------------
# PubMed verification
# ---------------------------------------------------------------------------

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def search_pubmed_by_doi(doi):
    """Search PubMed by DOI. Returns PMID or None."""
    url = f"{PUBMED_BASE}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(doi)}[doi]&retmode=json"
    data = _http_get_json(url)
    ids = data.get("esearchresult", {}).get("idlist", [])
    return ids[0] if ids else None


def search_pubmed_by_title(title):
    """Search PubMed by title. Returns (PMID, matched_title) or (None, None)."""
    clean = re.sub(r'[^\w\s]', ' ', title)
    url = f"{PUBMED_BASE}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(clean)}[ti]&retmode=json"
    data = _http_get_json(url)
    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return None, None
    # Fetch the title of the first result to verify similarity
    pmid = ids[0]
    fetch_url = f"{PUBMED_BASE}/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    summary = _http_get_json(fetch_url)
    result_data = summary.get("result", {})
    entry = result_data.get(pmid, {})
    matched_title = entry.get("title", "")
    sim = title_similarity(title, matched_title)
    if sim >= TITLE_SIMILARITY_THRESHOLD:
        return pmid, matched_title
    return None, None


def search_pubmed(meta):
    """Try DOI first, then title. Returns dict with pmid and search_method."""
    result = {"found": False, "pmid": None, "method": None, "similarity": None}
    if meta.get("doi"):
        pmid = search_pubmed_by_doi(meta["doi"])
        if pmid:
            result.update(found=True, pmid=pmid, method="doi")
            return result
    if meta.get("title"):
        pmid, matched = search_pubmed_by_title(meta["title"])
        if pmid:
            sim = title_similarity(meta["title"], matched)
            result.update(found=True, pmid=pmid, method="title", similarity=round(sim, 3))
            return result
    return result


# ---------------------------------------------------------------------------
# Semantic Scholar verification
# ---------------------------------------------------------------------------

S2_BASE = "https://api.semanticscholar.org/graph/v1"


def search_s2_by_doi(doi):
    """Look up a paper on Semantic Scholar by DOI."""
    url = f"{S2_BASE}/paper/DOI:{urllib.parse.quote(doi, safe='')}?fields=title,year,externalIds"
    data = _http_get_json(url)
    if "paperId" in data:
        return data
    return None


def search_s2_by_title(title):
    """Search Semantic Scholar by title. Returns best match or None (with similarity check)."""
    query = urllib.parse.quote(title[:200])
    url = f"{S2_BASE}/paper/search?query={query}&limit=3&fields=title,year,externalIds"
    data = _http_get_json(url)
    papers = data.get("data", [])
    for paper in papers:
        sim = title_similarity(title, paper.get("title", ""))
        if sim >= TITLE_SIMILARITY_THRESHOLD:
            paper["_similarity"] = round(sim, 3)
            return paper
    return None


def search_s2(meta):
    """Try DOI first, then title on Semantic Scholar."""
    result = {"found": False, "paper_id": None, "method": None, "matched_title": None, "similarity": None}
    if meta.get("doi"):
        paper = search_s2_by_doi(meta["doi"])
        if paper:
            result.update(found=True, paper_id=paper.get("paperId"), method="doi",
                          matched_title=paper.get("title"))
            return result
    if meta.get("title"):
        paper = search_s2_by_title(meta["title"])
        if paper:
            result.update(found=True, paper_id=paper.get("paperId"), method="title",
                          matched_title=paper.get("title"),
                          similarity=paper.get("_similarity"))
            return result
    return result


# ---------------------------------------------------------------------------
# CrossRef verification
# ---------------------------------------------------------------------------

CROSSREF_BASE = "https://api.crossref.org/works"


def search_crossref_by_doi(doi):
    """Verify a DOI exists on CrossRef."""
    url = f"{CROSSREF_BASE}/{urllib.parse.quote(doi, safe='')}"
    data = _http_get_json(url)
    if data and "message" in data:
        msg = data["message"]
        return {"found": True, "doi": msg.get("DOI"), "title": (msg.get("title") or [None])[0]}
    return {"found": False}


def search_crossref_by_title(title):
    """Search CrossRef by bibliographic query with similarity check."""
    query = urllib.parse.quote(title[:200])
    url = f"{CROSSREF_BASE}?query.bibliographic={query}&rows=3"
    data = _http_get_json(url)
    items = data.get("message", {}).get("items", [])
    for item in items:
        cr_title = (item.get("title") or [None])[0]
        if cr_title:
            sim = title_similarity(title, cr_title)
            if sim >= TITLE_SIMILARITY_THRESHOLD:
                return {"found": True, "doi": item.get("DOI"), "title": cr_title, "similarity": round(sim, 3)}
    return {"found": False}


def search_crossref(meta):
    """Try DOI first, then title on CrossRef."""
    result = {"found": False, "doi": None, "method": None, "similarity": None}
    if meta.get("doi"):
        cr = search_crossref_by_doi(meta["doi"])
        if cr.get("found"):
            result.update(found=True, doi=cr["doi"], method="doi")
            return result
    if meta.get("title"):
        cr = search_crossref_by_title(meta["title"])
        if cr.get("found"):
            result.update(found=True, doi=cr.get("doi"), method="title", similarity=cr.get("similarity"))
            return result
    return result


# ---------------------------------------------------------------------------
# Main verification pipeline
# ---------------------------------------------------------------------------

def verify_single_reference(idx, meta, delay=0.4):
    """Verify one reference across all three sources."""
    entry = {
        "index": idx,
        "raw": meta["raw"],
        "extracted_title": meta.get("title"),
        "extracted_doi": meta.get("doi"),
        "extracted_year": meta.get("year"),
        "pubmed": None,
        "semantic_scholar": None,
        "crossref": None,
        "status": "unverified",
    }

    # PubMed
    time.sleep(delay)
    entry["pubmed"] = search_pubmed(meta)

    # Semantic Scholar
    time.sleep(delay)
    entry["semantic_scholar"] = search_s2(meta)

    # CrossRef
    time.sleep(delay)
    entry["crossref"] = search_crossref(meta)

    # Determine overall status
    sources_found = sum([
        entry["pubmed"]["found"],
        entry["semantic_scholar"]["found"],
        entry["crossref"]["found"],
    ])
    if sources_found >= 2:
        entry["status"] = "verified"
    elif sources_found == 1:
        entry["status"] = "partially_verified"
    else:
        entry["status"] = "not_found"

    return entry


def run_verification(filepath, output_path=None):
    """Full verification pipeline: extract, parse, verify, report."""
    print(f"[1/4] Extracting text from: {filepath}")
    text = extract_text(filepath)
    if not text:
        sys.exit(f"Error: Could not extract text from {filepath}")

    print("[2/4] Extracting references section...")
    ref_text = extract_references_section(text)
    if not ref_text:
        print("  WARNING: Could not locate a References section. Attempting full-text parse...")
        ref_text = text

    print("[3/4] Parsing individual references...")
    raw_refs = parse_references(ref_text)
    print(f"  Found {len(raw_refs)} references.")

    if not raw_refs:
        report = {"manuscript": filepath, "total_references": 0, "results": [], "summary": {}}
        if output_path:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to {output_path}")
        return report

    print("[4/4] Verifying references against PubMed, Semantic Scholar, and CrossRef...")
    results = []
    for i, raw in enumerate(raw_refs, 1):
        meta = extract_citation_metadata(raw)
        print(f"  [{i}/{len(raw_refs)}] {(meta.get('title') or raw)[:70]}...")
        entry = verify_single_reference(i, meta)
        results.append(entry)

    # Summary
    verified = sum(1 for r in results if r["status"] == "verified")
    partial = sum(1 for r in results if r["status"] == "partially_verified")
    not_found = sum(1 for r in results if r["status"] == "not_found")

    summary = {
        "total": len(results),
        "verified": verified,
        "partially_verified": partial,
        "not_found": not_found,
        "verification_rate": f"{(verified + partial) / len(results) * 100:.1f}%" if results else "N/A",
    }

    report = {
        "manuscript": filepath,
        "total_references": len(results),
        "summary": summary,
        "results": results,
    }

    print(f"\n{'='*60}")
    print(f"  Verification Summary")
    print(f"{'='*60}")
    print(f"  Total references:      {summary['total']}")
    print(f"  Verified (2+ sources): {summary['verified']}")
    print(f"  Partially verified:    {summary['partially_verified']}")
    print(f"  Not found:             {summary['not_found']}")
    print(f"  Verification rate:     {summary['verification_rate']}")
    print(f"{'='*60}")

    if not_found > 0:
        print("\n  References NOT FOUND in any database:")
        for r in results:
            if r["status"] == "not_found":
                print(f"    [{r['index']}] {r['raw'][:100]}...")

    if partial > 0:
        print("\n  References only PARTIALLY verified (found in 1 source):")
        for r in results:
            if r["status"] == "partially_verified":
                print(f"    [{r['index']}] {r['raw'][:100]}...")

    if output_path:
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nFull report saved to: {output_path}")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Verify manuscript citations against PubMed, Semantic Scholar, and CrossRef."
    )
    parser.add_argument("manuscript", help="Path to manuscript file (.docx, .txt, .md)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output JSON report path (default: <manuscript>_citation_report.json)")
    args = parser.parse_args()

    if not os.path.isfile(args.manuscript):
        sys.exit(f"Error: File not found: {args.manuscript}")

    output = args.output
    if not output:
        base = os.path.splitext(args.manuscript)[0]
        output = f"{base}_citation_report.json"

    run_verification(args.manuscript, output)


if __name__ == "__main__":
    main()
