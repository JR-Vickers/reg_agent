"""SEC regulatory document scraper.

Scrapes enforcement actions and press releases from SEC's website,
filtering for crypto-related content.
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass
from uuid import UUID

import requests
from bs4 import BeautifulSoup

from src.database.client import get_supabase_client
from src.models.document import RegulationCreate, DocumentSource
from src.agents.monitor.federal_register import CRYPTO_KEYWORDS

logger = logging.getLogger(__name__)

SEC_PRESS_RSS = "https://www.sec.gov/news/pressreleases.rss"
SEC_LITIGATION_RSS = "https://www.sec.gov/enforcement-litigation/litigation-releases/rss"
SEC_BASE_URL = "https://www.sec.gov"


@dataclass
class ScrapedDocument:
    """A document scraped from the SEC."""
    document_id: str
    title: str
    url: str
    published_date: Optional[datetime]
    description: Optional[str]
    doc_type: str
    content: Optional[str] = None


HEADERS = {
    "User-Agent": "RegAgent jarrett_vickers@yahoo.com"
}


def fetch_rss(url: str) -> str:
    """Fetch RSS feed content."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def fetch_page_content(url: str, max_length: int = 50000) -> Optional[str]:
    """Fetch and extract text content from an SEC page."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        main_content = soup.find("div", class_="article-body") or soup.find("main") or soup.body
        if main_content:
            text = main_content.get_text(separator=" ", strip=True)
        else:
            text = soup.get_text(separator=" ", strip=True)

        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > max_length:
            text = text[:max_length]

        return text
    except Exception as e:
        logger.warning(f"Failed to fetch content from {url}: {e}")
        return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string from RSS feed."""
    if not date_str:
        return None

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
        "%B %d, %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=None)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return None


def extract_document_id(url: str) -> str:
    """Extract or generate a unique document ID from URL."""
    match = re.search(r'/(\d{4}-\d+)', url)
    if match:
        return f"SEC-{match.group(1)}"

    match = re.search(r'lr-?(\d+)', url, re.IGNORECASE)
    if match:
        return f"SEC-LR-{match.group(1)}"

    return f"SEC-{hashlib.sha256(url.encode()).hexdigest()[:12]}"


def is_crypto_related(text: str) -> bool:
    """Check if text contains crypto-related keywords."""
    if not text:
        return False
    text_lower = text.lower()
    for keyword in CRYPTO_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    return False


def parse_rss_feed(xml_content: str, doc_type: str) -> List[ScrapedDocument]:
    """Parse RSS feed XML into documents."""
    soup = BeautifulSoup(xml_content, "html.parser")
    documents = []

    items = soup.find_all("item")
    for item in items:
        title_tag = item.find("title")
        link_tag = item.find("link")
        pub_date_tag = item.find("pubdate")
        desc_tag = item.find("description")

        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        description = desc_tag.get_text(strip=True) if desc_tag else None

        url = ""
        if link_tag:
            url = link_tag.get_text(strip=True)
            if not url and link_tag.next_sibling:
                url = str(link_tag.next_sibling).strip()

        if not url:
            continue

        combined_text = f"{title} {description or ''}"
        if not is_crypto_related(combined_text):
            continue

        if url.startswith("/"):
            url = f"{SEC_BASE_URL}{url}"

        pub_date = None
        if pub_date_tag:
            pub_date = parse_date(pub_date_tag.get_text(strip=True))

        doc = ScrapedDocument(
            document_id=extract_document_id(url),
            title=title,
            url=url,
            published_date=pub_date,
            description=description,
            doc_type=doc_type,
        )
        documents.append(doc)

    return documents


def scrape_sec(days_back: int = 30) -> List[ScrapedDocument]:
    """Scrape crypto-related documents from SEC RSS feeds."""
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    all_documents = []
    seen_ids = set()

    try:
        logger.info("Fetching SEC press releases RSS")
        press_xml = fetch_rss(SEC_PRESS_RSS)
        press_docs = parse_rss_feed(press_xml, "press_release")
        logger.info(f"Found {len(press_docs)} crypto-related press releases")

        for doc in press_docs:
            if doc.document_id not in seen_ids:
                if doc.published_date is None or doc.published_date >= cutoff_date:
                    seen_ids.add(doc.document_id)
                    all_documents.append(doc)
    except Exception as e:
        logger.error(f"Failed to fetch SEC press releases: {e}")

    try:
        logger.info("Fetching SEC litigation releases RSS")
        lit_xml = fetch_rss(SEC_LITIGATION_RSS)
        lit_docs = parse_rss_feed(lit_xml, "litigation_release")
        logger.info(f"Found {len(lit_docs)} crypto-related litigation releases")

        for doc in lit_docs:
            if doc.document_id not in seen_ids:
                if doc.published_date is None or doc.published_date >= cutoff_date:
                    seen_ids.add(doc.document_id)
                    all_documents.append(doc)
    except Exception as e:
        logger.error(f"Failed to fetch SEC litigation releases: {e}")

    logger.info(f"SEC scrape found {len(all_documents)} unique crypto-related documents")
    return all_documents


def ingest_new_documents(days_back: int = 30) -> int:
    """Scrape SEC and store new documents in database."""
    db = get_supabase_client()
    documents = scrape_sec(days_back=days_back)

    new_count = 0
    for doc in documents:
        exists = db.regulation_exists(
            source=DocumentSource.SEC.value,
            document_id=doc.document_id,
        )

        if exists:
            logger.debug(f"Skipping existing document: {doc.title}")
            continue

        content = fetch_page_content(doc.url) if doc.url else None
        if not content:
            content = doc.description

        regulation = RegulationCreate(
            source=DocumentSource.SEC,
            document_id=doc.document_id,
            title=doc.title,
            url=doc.url,
            published_date=doc.published_date,
            content=content,
            metadata={"doc_type": doc.doc_type},
        )

        try:
            result = db.create_regulation(regulation)
            logger.info(f"Stored new SEC document: {doc.title}")
            new_count += 1

            try:
                from src.agents.classify.pipeline import classify_and_store
                classify_and_store(
                    regulation_id=UUID(result["id"]),
                    title=doc.title,
                    source=DocumentSource.SEC.value,
                    published_date=str(doc.published_date or ""),
                    content=content or doc.title,
                )
            except Exception as e:
                logger.error(f"Auto-classify failed for {doc.title}: {e}")

        except Exception as e:
            logger.error(f"Failed to store document {doc.title}: {e}")

    logger.info(f"Ingested {new_count} new documents from SEC")
    return new_count


def backfill(days: int = 90) -> int:
    """Backfill historical documents from the past N days."""
    logger.info(f"Backfilling SEC documents from past {days} days")
    return ingest_new_documents(days_back=days)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    docs = scrape_sec(days_back=90)
    print(f"\nFound {len(docs)} crypto-related documents:\n")
    for doc in docs[:10]:
        print(f"  [{doc.doc_type}] {doc.title}")
        print(f"    URL: {doc.url}")
        print(f"    Date: {doc.published_date}")
        print()
