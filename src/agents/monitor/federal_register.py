"""Federal Register regulatory document monitor.

Queries the Federal Register API for crypto/BSA/AML-related documents.
API docs: https://www.federalregister.gov/developers/api/v1
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass
from uuid import UUID

import requests

from src.database.client import get_supabase_client
from src.models.document import RegulationCreate, DocumentSource

logger = logging.getLogger(__name__)

FR_API_BASE = "https://www.federalregister.gov/api/v1"

CRYPTO_KEYWORDS = [
    "cryptocurrency", "crypto-asset", "crypto asset",
    "virtual currency", "virtual asset",
    "digital asset", "digital currency", "digital token",
    "blockchain", "distributed ledger",
    "Bitcoin", "Ether", "Ethereum", "Ripple", "XRP",
    "Litecoin", "Solana", "Cardano", "Polkadot", "Avalanche",
    "Chainlink", "Polygon", "MATIC", "Dogecoin", "Shiba Inu",
    "Tether", "USDC", "stablecoin", "stablecoins",
    "DeFi", "decentralized finance",
    "NFT", "non-fungible token",
    "smart contract", "token offering",
    "initial coin offering",
    "security token", "utility token",
    "crypto exchange", "crypto trading",
    "crypto custody", "digital wallet",
    "proof of stake", "proof of work",
    "money services business", "money transmitter",
    "Bank Secrecy Act", "BSA", "anti-money laundering", "AML",
    "know your customer", "KYC",
    "FinCEN", "OFAC", "sanctions",
    "suspicious activity report", "SAR",
    "currency transaction report", "CTR",
    "money laundering", "terrorist financing",
    "convertible virtual currency", "CVC",
    "unhosted wallet", "self-hosted wallet",
    "travel rule", "funds transfer rule",
    "BitLicense", "MiCA",
    "Web3", "DAO", "decentralized autonomous organization",
]


@dataclass
class ScrapedDocument:
    """A document fetched from the Federal Register API."""
    document_id: str
    title: str
    url: str
    published_date: Optional[datetime]
    description: Optional[str]
    doc_type: str
    agencies: List[str]


def search_documents(
    keyword: str,
    per_page: int = 100,
    page: int = 1,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Query the Federal Register API for documents matching a keyword."""
    params = {
        "conditions[term]": keyword,
        "conditions[type][]": ["RULE", "PRORULE", "NOTICE"],
        "per_page": per_page,
        "page": page,
        "order": "newest",
        "fields[]": [
            "document_number", "title", "html_url",
            "publication_date", "abstract", "type",
            "agencies", "docket_ids",
        ],
    }
    if start_date:
        params["conditions[publication_date][gte]"] = start_date
    if end_date:
        params["conditions[publication_date][lte]"] = end_date

    response = requests.get(f"{FR_API_BASE}/documents.json", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_all_keyword_results(
    keyword: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_pages: int = 5,
) -> List[dict]:
    """Fetch all pages of results for a keyword (up to max_pages)."""
    all_results = []
    page = 1
    while page <= max_pages:
        data = search_documents(keyword, page=page, start_date=start_date, end_date=end_date)
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        if page >= data.get("total_pages", 1):
            break
        page += 1
    return all_results


def parse_result(result: dict) -> Optional[ScrapedDocument]:
    """Parse a single API result into a ScrapedDocument."""
    doc_number = result.get("document_number")
    title = result.get("title")
    if not doc_number or not title:
        return None

    pub_date = None
    if result.get("publication_date"):
        try:
            pub_date = datetime.strptime(result["publication_date"], "%Y-%m-%d")
        except ValueError:
            pass

    agencies = [a.get("name", "") for a in result.get("agencies", []) if a.get("name")]
    doc_type_map = {"Rule": "rule", "Proposed Rule": "proposed_rule", "Notice": "notice"}
    doc_type = doc_type_map.get(result.get("type", ""), "other")

    return ScrapedDocument(
        document_id=doc_number,
        title=title,
        url=result.get("html_url", f"https://www.federalregister.gov/d/{doc_number}"),
        published_date=pub_date,
        description=result.get("abstract"),
        doc_type=doc_type,
        agencies=agencies,
    )


def scrape_federal_register(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[ScrapedDocument]:
    """Search the Federal Register for all crypto/BSA-related documents."""
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    seen_ids = set()
    all_documents = []

    for keyword in CRYPTO_KEYWORDS:
        try:
            results = fetch_all_keyword_results(keyword, start_date=start_date, end_date=end_date)
            for result in results:
                doc = parse_result(result)
                if doc and doc.document_id not in seen_ids:
                    seen_ids.add(doc.document_id)
                    all_documents.append(doc)
        except Exception as e:
            logger.warning(f"Failed to search for keyword '{keyword}': {e}")
            continue

    logger.info(f"Federal Register search found {len(all_documents)} unique documents")
    return all_documents


def ingest_new_documents(start_date: Optional[str] = None) -> int:
    """Search Federal Register and store new documents in database."""
    db = get_supabase_client()
    documents = scrape_federal_register(start_date=start_date)

    new_count = 0
    for doc in documents:
        exists = db.regulation_exists(
            source=DocumentSource.FEDERAL_REGISTER.value,
            document_id=doc.document_id,
        )

        if exists:
            logger.debug(f"Skipping existing document: {doc.title}")
            continue

        regulation = RegulationCreate(
            source=DocumentSource.FEDERAL_REGISTER,
            document_id=doc.document_id,
            title=doc.title,
            url=doc.url,
            published_date=doc.published_date,
            content=doc.description,
            metadata={
                "doc_type": doc.doc_type,
                "agencies": doc.agencies,
            },
        )

        try:
            result = db.create_regulation(regulation)
            logger.info(f"Stored new document: {doc.title}")
            new_count += 1

            try:
                from src.agents.classify.pipeline import classify_and_store
                classify_and_store(
                    regulation_id=UUID(result["id"]),
                    title=doc.title,
                    source=DocumentSource.FEDERAL_REGISTER.value,
                    published_date=str(doc.published_date or ""),
                    content=doc.description or doc.title,
                )
            except Exception as e:
                logger.error(f"Auto-classify failed for {doc.title}: {e}")

        except Exception as e:
            logger.error(f"Failed to store document {doc.title}: {e}")

    logger.info(f"Ingested {new_count} new documents from Federal Register")
    return new_count


def backfill(months: int = 12) -> int:
    """Backfill historical documents from the past N months."""
    start_date = (datetime.utcnow() - timedelta(days=months * 30)).strftime("%Y-%m-%d")
    logger.info(f"Backfilling Federal Register from {start_date}")
    return ingest_new_documents(start_date=start_date)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    docs = scrape_federal_register(
        start_date=(datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    )
    print(f"\nFound {len(docs)} documents:\n")
    for doc in docs[:10]:
        print(f"  [{doc.doc_type}] {doc.title}")
        print(f"    Agencies: {', '.join(doc.agencies)}")
        print(f"    URL: {doc.url}")
        print(f"    Date: {doc.published_date}")
        print()
