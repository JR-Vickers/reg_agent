"""Supabase client wrapper for easier integration."""

from typing import List, Dict, Any, Optional
import logging
from uuid import UUID

from supabase import create_client, Client
from src.config.settings import settings
from src.models.document import (
    Regulation, Classification, GapAnalysis,
    RegulationCreate, ClassificationCreate, GapAnalysisCreate,
    TaskCreate, TaskUpdate,
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

    def get_regulation_counts(self) -> Dict[str, int]:
        """Get total count and counts by source using count query."""
        try:
            total_resp = self.client.table("regulations").select("*", count="exact").limit(0).execute()
            total = total_resp.count or 0

            source_resp = self.client.table("regulations").select("source").execute()
            source_counts = {}
            for row in source_resp.data:
                src = row.get("source", "unknown")
                source_counts[src] = source_counts.get(src, 0) + 1

            return {"total": total, "by_source": source_counts}

        except Exception as e:
            logger.error(f"Error getting regulation counts: {e}")
            return {"total": 0, "by_source": {}}

    def get_regulation_by_document_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.table("regulations").select("*").eq(
                "document_id", document_id
            ).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching regulation by document_id {document_id}: {e}")
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
            data = classification.model_dump(mode="json", exclude_none=True)
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
            data = gap_analysis.model_dump(mode="json", exclude_none=True)
            response = self.client.table("gap_analyses").insert(data).execute()

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

    def get_gap_analysis_by_id(
        self,
        gap_analysis_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get gap analysis by its own ID."""
        try:
            response = self.client.table("gap_analyses").select("*").eq(
                "id", str(gap_analysis_id)
            ).execute()

            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Error fetching gap analysis {gap_analysis_id}: {e}")
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

    def get_classifications_needing_gap_analysis(
        self,
        relevance_threshold: int = 3,
        confidence_threshold: float = 0.7,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get classifications that meet threshold but lack gap analysis."""
        try:
            response = self.client.from_("classifications").select(
                "regulation_id, relevance_score, confidence, bsa_pillars, categories, classification_reasoning, regulations(id, title, source, published_date, content)"
            ).gte("relevance_score", relevance_threshold).gte("confidence", confidence_threshold).limit(limit).execute()

            results = []
            for row in response.data:
                reg_id = row["regulation_id"]
                existing_gap = self.get_gap_analysis(UUID(reg_id))
                if not existing_gap:
                    results.append(row)

            return results

        except Exception as e:
            logger.error(f"Error fetching classifications needing gap analysis: {e}")
            return []

    # Tasks

    def create_task(self, task: TaskCreate) -> Dict[str, Any]:
        """Create a new task."""
        try:
            data = task.model_dump(mode="json", exclude_none=True)
            response = self.client.table("tasks").insert(data).execute()

            if not response.data:
                raise ValueError("Failed to create task")

            return response.data[0]

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise

    def get_task(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        try:
            response = self.client.table("tasks").select("*").eq(
                "id", str(task_id)
            ).execute()

            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Error fetching task {task_id}: {e}")
            raise

    def get_tasks(
        self,
        status: Optional[str] = None,
        assigned_team: Optional[str] = None,
        priority: Optional[str] = None,
        regulation_id: Optional[UUID] = None,
        gap_analysis_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get tasks with optional filtering."""
        try:
            query = self.client.table("tasks").select("*")

            if status:
                query = query.eq("status", status)
            if assigned_team:
                query = query.eq("assigned_team", assigned_team)
            if priority:
                query = query.eq("priority", priority)
            if regulation_id:
                query = query.eq("regulation_id", str(regulation_id))
            if gap_analysis_id:
                query = query.eq("gap_analysis_id", str(gap_analysis_id))

            query = query.order("created_at", desc=True)
            query = query.range(offset, offset + limit - 1)

            response = query.execute()
            return response.data

        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")
            raise

    def update_task(self, task_id: UUID, update: TaskUpdate) -> Dict[str, Any]:
        """Update a task."""
        try:
            data = update.model_dump(mode="json", exclude_none=True)
            if not data:
                raise ValueError("No update fields provided")

            response = self.client.table("tasks").update(data).eq(
                "id", str(task_id)
            ).execute()

            if not response.data:
                raise ValueError(f"Task {task_id} not found")

            return response.data[0]

        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            raise

    def get_tasks_by_gap_analysis(self, gap_analysis_id: UUID) -> List[Dict[str, Any]]:
        """Get all tasks for a gap analysis."""
        try:
            response = self.client.table("tasks").select("*").eq(
                "gap_analysis_id", str(gap_analysis_id)
            ).execute()

            return response.data

        except Exception as e:
            logger.error(f"Error fetching tasks for gap analysis {gap_analysis_id}: {e}")
            raise

    def get_distinct_teams(self) -> List[str]:
        """Get list of distinct assigned teams."""
        try:
            response = self.client.table("tasks").select("assigned_team").execute()
            teams = set(row["assigned_team"] for row in response.data)
            return sorted(teams)

        except Exception as e:
            logger.error(f"Error fetching distinct teams: {e}")
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