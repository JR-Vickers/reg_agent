"""Supabase client wrapper for easier integration."""

from typing import List, Dict, Any, Optional
import logging
from uuid import UUID

from supabase import create_client, Client
from src.config.settings import settings
from src.models.document import (
    Regulation, Classification, GapAnalysis,
    RegulationCreate, ClassificationCreate, GapAnalysisCreate
)

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Wrapper for Supabase client with type safety and error handling."""

    def __init__(self):
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise ValueError("Supabase URL and anon key must be provided")

        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key
        )

    # Regulations

    def create_regulation(self, regulation: RegulationCreate) -> Dict[str, Any]:
        """Create a new regulation document."""
        try:
            response = self.client.table("regulations").insert(
                regulation.model_dump(mode="json", exclude_none=True)
            ).execute()

            if not response.data:
                raise ValueError("Failed to create regulation")

            return response.data[0]

        except Exception as e:
            logger.error(f"Error creating regulation: {e}")
            raise

    def get_regulation(self, regulation_id: UUID) -> Optional[Dict[str, Any]]:
        """Get regulation by ID."""
        try:
            response = self.client.table("regulations").select("*").eq(
                "id", str(regulation_id)
            ).execute()

            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Error fetching regulation {regulation_id}: {e}")
            raise

    def get_regulations(
        self,
        source: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get regulations with optional filtering."""
        try:
            query = self.client.table("regulations").select("*")

            if source:
                query = query.eq("source", source)

            query = query.order("published_date", desc=True)
            query = query.range(offset, offset + limit - 1)

            response = query.execute()
            return response.data

        except Exception as e:
            logger.error(f"Error fetching regulations: {e}")
            raise

    def regulation_exists(self, source: str, document_id: str) -> bool:
        """Check if regulation already exists."""
        try:
            response = self.client.table("regulations").select("id").eq(
                "source", source
            ).eq("document_id", document_id).execute()

            return len(response.data) > 0

        except Exception as e:
            logger.error(f"Error checking regulation existence: {e}")
            return False

    # Classifications

    def create_classification(
        self,
        classification: ClassificationCreate
    ) -> Dict[str, Any]:
        """Create a new classification."""
        try:
            # Convert enum to int for database storage
            data = classification.model_dump(exclude_none=True)
            data["relevance_score"] = int(data["relevance_score"])

            response = self.client.table("classifications").insert(data).execute()

            if not response.data:
                raise ValueError("Failed to create classification")

            return response.data[0]

        except Exception as e:
            logger.error(f"Error creating classification: {e}")
            raise

    def get_classification(
        self,
        regulation_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get classification for a regulation."""
        try:
            response = self.client.table("classifications").select("*").eq(
                "regulation_id", str(regulation_id)
            ).execute()

            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Error fetching classification for {regulation_id}: {e}")
            raise

    # Gap Analyses

    def create_gap_analysis(
        self,
        gap_analysis: GapAnalysisCreate
    ) -> Dict[str, Any]:
        """Create a new gap analysis."""
        try:
            response = self.client.table("gap_analyses").insert(
                gap_analysis.model_dump(exclude_none=True)
            ).execute()

            if not response.data:
                raise ValueError("Failed to create gap analysis")

            return response.data[0]

        except Exception as e:
            logger.error(f"Error creating gap analysis: {e}")
            raise

    def get_gap_analysis(
        self,
        regulation_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get gap analysis for a regulation."""
        try:
            response = self.client.table("gap_analyses").select("*").eq(
                "regulation_id", str(regulation_id)
            ).execute()

            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Error fetching gap analysis for {regulation_id}: {e}")
            raise

    # Complex Queries

    def get_recent_regulations(self, days: int = 90) -> List[Dict[str, Any]]:
        """Get recent regulations with classifications using view."""
        try:
            response = self.client.rpc(
                "recent_regulations_view",
                {"days_back": days}
            ).execute()

            return response.data

        except Exception as e:
            logger.error(f"Error fetching recent regulations: {e}")
            # Fallback to simple query
            return self.get_regulations(limit=50)

    def get_priority_regulations(self) -> List[Dict[str, Any]]:
        """Get high-priority regulations requiring attention."""
        try:
            response = self.client.table("priority_regulations").select("*").execute()
            return response.data

        except Exception as e:
            logger.error(f"Error fetching priority regulations: {e}")
            return []

    # Vector Search (for future use)

    def search_similar_regulations(
        self,
        embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Search for similar regulations using vector similarity."""
        try:
            # This requires a custom RPC function in Supabase
            response = self.client.rpc(
                "search_similar_regulations",
                {
                    "query_embedding": embedding,
                    "match_threshold": similarity_threshold,
                    "match_count": limit
                }
            ).execute()

            return response.data

        except Exception as e:
            logger.warning(f"Vector search not available: {e}")
            return []


# Global Supabase client instance
supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get Supabase client (dependency injection)."""
    global supabase_client
    if not supabase_client:
        supabase_client = SupabaseClient()
    return supabase_client