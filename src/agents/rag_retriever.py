"""
AstroGeo RAG Retriever
=======================
pgvector-based semantic search for all agent domains.
Falls back to mock results if pgvector is not available.

Author: Production Team
Version: 1.0.0
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    Semantic retrieval from pgvector-enabled PostgreSQL.

    Supports 5 vector tables:
    - change_event_embeddings    (Agent 1: Satellite Change)
    - asteroid_obs_embeddings    (Agent 2: Asteroid Planner)
    - drought_event_embeddings   (Agent 3: Drought Intelligence)
    - prediction_embeddings      (Agent 4: Ground Truth)
    - graph_node_embeddings      (Agent 5: GraphRAG)
    """

    VALID_TABLES = {
        "change_event_embeddings",
        "asteroid_obs_embeddings",
        "drought_event_embeddings",
        "prediction_embeddings",
        "graph_node_embeddings",
    }

    def __init__(self, db: AsyncSession, use_openai: bool = True):
        self.db = db
        self._use_openai = use_openai
        self._embedding_cache: Dict[str, List[float]] = {}

    async def embed_text(self, text_input: str) -> List[float]:
        """Generate embedding vector for text."""
        if text_input in self._embedding_cache:
            return self._embedding_cache[text_input]

        # Try OpenAI embeddings
        if self._use_openai:
            try:
                from src.core.config import settings

                if settings.OPENAI_API_KEY:
                    from openai import AsyncOpenAI

                    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    response = await client.embeddings.create(
                        input=text_input,
                        model="text-embedding-3-small",
                    )
                    embedding = response.data[0].embedding
                    self._embedding_cache[text_input] = embedding
                    return embedding
            except Exception as e:
                logger.warning(f"OpenAI embedding failed, using fallback: {e}")

        # Fallback: sentence-transformers (local, no API key needed)
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer("all-MiniLM-L6-v2")
            embedding = model.encode(text_input).tolist()
            # Pad/truncate to 1536 dims to match OpenAI format
            if len(embedding) < 1536:
                embedding = embedding + [0.0] * (1536 - len(embedding))
            else:
                embedding = embedding[:1536]
            self._embedding_cache[text_input] = embedding
            return embedding
        except Exception as e:
            logger.warning(f"sentence-transformers failed: {e}")

        # Last resort: random embedding (for demo only)
        logger.warning("Using random embedding — results will be random")
        embedding = np.random.randn(1536).tolist()
        return embedding

    async def search(
        self,
        query: str,
        table: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Semantic similarity search using pgvector cosine distance.
        Returns top_k most similar documents.
        """
        if table not in self.VALID_TABLES:
            logger.warning(f"Invalid table: {table}, using graph_node_embeddings")
            table = "graph_node_embeddings"

        try:
            query_embedding = await self.embed_text(query)
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            sql = text(f"""
                SELECT
                    id,
                    summary_text,
                    1 - (embedding <=> :embedding::vector) AS similarity
                FROM {table}
                WHERE 1 - (embedding <=> :embedding::vector) > :min_sim
                ORDER BY embedding <=> :embedding::vector
                LIMIT :top_k
            """)

            result = await self.db.execute(
                sql,
                {
                    "embedding": embedding_str,
                    "min_sim": min_similarity,
                    "top_k": top_k,
                },
            )

            rows = result.fetchall()

            documents = []
            for row in rows:
                row_dict = dict(row._mapping)
                documents.append(
                    {
                        "id": str(row_dict.get("id")),
                        "summary": row_dict.get("summary_text", ""),
                        "similarity": float(row_dict.get("similarity", 0)),
                        "source": table,
                        "metadata": {},
                    }
                )

            logger.info(f"RAG search: {len(documents)} results from {table}")
            return documents

        except Exception as e:
            logger.error(f"pgvector search failed: {e}")
            return self._get_mock_results(query, table, top_k)

    def _get_mock_results(self, query: str, table: str, top_k: int) -> List[Dict]:
        """Demo fallback results when pgvector is unavailable."""
        mock_data = {
            "asteroid_obs_embeddings": [
                {
                    "summary": "Asteroid 2024 BX1 observed successfully from Mumbai, 84% success rate in similar conditions.",
                    "similarity": 0.91,
                },
                {
                    "summary": "High asteroid visibility during new moon phase — 12/14 observations successful.",
                    "similarity": 0.87,
                },
                {
                    "summary": "Mumbai observer reports: cloud cover below 30% critical for magnitude 18+ objects.",
                    "similarity": 0.82,
                },
            ],
            "change_event_embeddings": [
                {
                    "summary": "Maharashtra NDVI decline 2023: -42% rainfall anomaly linked to vegetation stress.",
                    "similarity": 0.89,
                },
                {
                    "summary": "Western Ghats deforestation hotspot detected Oct 2023, 1,200 ha affected.",
                    "similarity": 0.85,
                },
            ],
            "drought_event_embeddings": [
                {
                    "summary": "Osmanabad district drought Level 3 warning, soil moisture 0.09 m³/m³ (below 0.15 threshold).",
                    "similarity": 0.88,
                },
                {
                    "summary": "2019 Maharashtra drought: similar SMAP readings preceded Level 4 emergency.",
                    "similarity": 0.83,
                },
            ],
            "graph_node_embeddings": [
                {
                    "summary": "Cross-domain event: NDVI decline in Maharashtra correlates with -42% ERA5 rainfall.",
                    "similarity": 0.87,
                },
            ],
            "prediction_embeddings": [
                {
                    "summary": "Verified prediction: asteroid visible from Pune 2024-10-14, confidence was 82%, outcome TRUE.",
                    "similarity": 0.86,
                },
            ],
        }
        results = mock_data.get(
            table, [{"summary": f"Historical data for: {query}", "similarity": 0.75}]
        )
        return [
            {
                **r,
                "id": str(np.random.randint(1000, 9999)),
                "source": table,
                "metadata": {},
            }
            for r in results[:top_k]
        ]

    async def upsert_document(
        self,
        table: str,
        document: Dict[str, Any],
        text_field: str = "summary_text",
    ) -> bool:
        """Embed and store a document in the vector store."""
        try:
            text_to_embed = document.get(text_field, "")
            if not text_to_embed:
                return False

            embedding = await self.embed_text(text_to_embed)
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            fields = {k: v for k, v in document.items()}
            fields["embedding"] = embedding_str

            columns = ", ".join(fields.keys())
            placeholders = ", ".join(
                [
                    f":{k}" if k != "embedding" else f"'{embedding_str}'::vector"
                    for k in fields.keys()
                ]
            )

            sql = text(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            )
            params = {k: v for k, v in fields.items() if k != "embedding"}

            await self.db.execute(sql, params)
            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Upsert failed: {e}")
            return False
