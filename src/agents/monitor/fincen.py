"""FinCEN regulatory document scraper.

Scrapes advisories, alerts, and notices from FinCEN's public website.
"""

import hashlib
import logging
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from src.database.client import get_supabase_client
from src.models.document import RegulationCreate, DocumentSource

logger = logging.getLogger(__name__)

FINCEN_URL = "https://www.fincen.gov/resources/advisoriesbulletinsfact-sheets"


@dataclass
class ScrapedDocument:
    """A document scraped from FinCEN."""
    document_id: str
    title: str
    url: str
    published_date: Optional[datetime]
    description: Optional[str]
    doc_type: str  # 'alert', 'advisory', 'notice'


def fetch_page(url: str) -> str:
    """Fetch HTML content from URL."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not date_str:
        return None

    date_str = date_str.strip()
    formats = [
        "%B %d, %Y",   # "January 15, 2025"
        "%b %d, %Y",   # "Jan 15, 2025"
        "%m/%d/%Y",    # "01/15/2025"
        "%Y-%m-%d",    # "2025-01-15"
        "%m/%Y",       # "12/2020" (day defaults to 1)
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return None


def extract_document_id(url: str, title: str) -> str:
    """Extract or generate a unique document ID."""
    if "FIN-" in title.upper():
        for part in title.split():
            if part.upper().startswith("FIN-"):
                return part.upper()

    return hashlib.sha256(url.encode()).hexdigest()[:16]


def parse_table_section(table: BeautifulSoup, doc_type: str) -> List[ScrapedDocument]:
    """Parse a table section and extract documents."""
    documents = []

    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        link = cells[0].find("a")
        if not link:
            continue

        title = link.get_text(strip=True)
        href = link.get("href", "")

        if href.startswith("/"):
            url = f"https://www.fincen.gov{href}"
        elif not href.startswith("http"):
            url = f"https://www.fincen.gov/{href}"
        else:
            url = href

        date_str = cells[1].get_text(strip=True) if len(cells) > 1 else None
        description = cells[2].get_text(strip=True) if len(cells) > 2 else None

        doc = ScrapedDocument(
            document_id=extract_document_id(url, title),
            title=title,
            url=url,
            published_date=parse_date(date_str),
            description=description,
            doc_type=doc_type,
        )
        documents.append(doc)

    return documents


def scrape_fincen() -> List[ScrapedDocument]:
    """Scrape all documents from FinCEN advisories page."""
    logger.info(f"Fetching FinCEN page: {FINCEN_URL}")
    html = fetch_page(FINCEN_URL)
    soup = BeautifulSoup(html, "html.parser")

    all_documents = []

    tables = soup.find_all("table")
    logger.info(f"Found {len(tables)} tables on page")

    section_types = ["alert", "advisory", "notice", "fact_sheet"]

    for i, table in enumerate(tables):
        doc_type = section_types[i] if i < len(section_types) else f"section_{i}"
        docs = parse_table_section(table, doc_type)
        logger.info(f"Found {len(docs)} documents in {doc_type} section")
        all_documents.extend(docs)

    return all_documents


def ingest_new_documents() -> int:
    """Scrape FinCEN and store new documents in database."""
    db = get_supabase_client()
    documents = scrape_fincen()

    new_count = 0
    for doc in documents:
        exists = db.regulation_exists(
            source=DocumentSource.FINCEN.value,
            document_id=doc.document_id
        )

        if exists:
            logger.debug(f"Skipping existing document: {doc.title}")
            continue

        regulation = RegulationCreate(
            source=DocumentSource.FINCEN,
            document_id=doc.document_id,
            title=doc.title,
            url=doc.url,
            published_date=doc.published_date,
            content=doc.description,
            metadata={"doc_type": doc.doc_type},
        )

        try:
            db.create_regulation(regulation)
            logger.info(f"Stored new document: {doc.title}")
            new_count += 1
        except Exception as e:
            logger.error(f"Failed to store document {doc.title}: {e}")

    logger.info(f"Ingested {new_count} new documents from FinCEN")
    return new_count


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    docs = scrape_fincen()
    print(f"\nScraped {len(docs)} documents:\n")
    for doc in docs[:10]:
        print(f"  [{doc.doc_type}] {doc.title}")
        print(f"    URL: {doc.url}")
        print(f"    Date: {doc.published_date}")
        print()
