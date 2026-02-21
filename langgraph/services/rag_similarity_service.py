"""
RAG similarity retrieval service with graceful fallback.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import config


class SimilarityRetrievalService:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self._chroma_client = None

    def retrieve_similar_cases(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if not config.FEATURE_FLAGS["enable_rag_similarity"]:
            return {
                "cases": [],
                "stats": {
                    "enabled": False,
                    "method": "disabled",
                    "hits": 0,
                    "misses": 0,
                },
                "plan": [],
            }

        sku_id = state.get("sku_id")
        store_id = state.get("store_id")

        fallback_cases = self._fetch_historical_cases(sku_id=sku_id, store_id=store_id)
        self._record_index_metadata(state=state, historical_cases=fallback_cases)

        plan: List[str] = []
        chroma_cases: List[Dict[str, Any]] = []
        chroma_error: Optional[str] = None

        try:
            collection = self._get_chroma_collection()
            if collection is not None:
                self._upsert_cases_into_collection(collection, fallback_cases)
                query_text = self._build_query_text(state)
                result = collection.query(
                    query_texts=[query_text],
                    n_results=config.RAG_CONFIG["retrieval_k"],
                )
                chroma_cases = self._format_chroma_result(result)
        except Exception as exc:
            chroma_error = str(exc)
            print(f"  [RAG Similarity] Chroma unavailable: {exc}")

        if chroma_cases:
            return {
                "cases": chroma_cases,
                "stats": {
                    "enabled": True,
                    "method": "chroma",
                    "hits": len(chroma_cases),
                    "misses": 0,
                    "chroma_error": None,
                },
                "plan": [],
            }

        if chroma_error:
            plan = self._build_chroma_spinup_plan(chroma_error)

        return {
            "cases": fallback_cases,
            "stats": {
                "enabled": True,
                "method": "postgres_fallback",
                "hits": len(fallback_cases),
                "misses": 0 if fallback_cases else 1,
                "chroma_error": chroma_error,
            },
            "plan": plan,
        }

    def _fetch_historical_cases(self, sku_id: int, store_id: int) -> List[Dict[str, Any]]:
        try:
            return self.mcp_client.call_tool(
                "postgres",
                "get_historical_promotion_cases",
                {"sku_id": sku_id, "store_id": store_id, "limit": config.RAG_CONFIG["retrieval_k"]},
            ) or []
        except Exception as exc:
            print(f"  [RAG Similarity] Historical fallback query failed: {exc}")
            return []

    def _record_index_metadata(self, state: Dict[str, Any], historical_cases: List[Dict[str, Any]]) -> None:
        sku_id = state.get("sku_id")
        store_id = state.get("store_id")
        inventory = state.get("inventory_data", {})

        try:
            self.mcp_client.call_tool(
                "postgres",
                "upsert_embedding_metadata",
                {
                    "entity_type": "sku",
                    "entity_id": int(sku_id),
                    "sku_id": sku_id,
                    "store_id": store_id,
                    "embedding_provider": "chroma",
                    "collection_name": config.RAG_CONFIG["chroma_collection"],
                    "vector_key": f"sku-{sku_id}",
                    "source_payload": inventory,
                    "summary": f"SKU metadata index for SKU {sku_id} at store {store_id}",
                },
            )
        except Exception as exc:
            print(f"  [RAG Similarity] Failed to log SKU embedding metadata: {exc}")

        for case in historical_cases:
            promotion_id = case.get("promotion_id")
            if not promotion_id:
                continue
            try:
                self.mcp_client.call_tool(
                    "postgres",
                    "upsert_embedding_metadata",
                    {
                        "entity_type": "promotion",
                        "entity_id": int(promotion_id),
                        "sku_id": case.get("sku_id"),
                        "store_id": case.get("store_id"),
                        "promotion_id": int(promotion_id),
                        "embedding_provider": "chroma",
                        "collection_name": config.RAG_CONFIG["chroma_collection"],
                        "vector_key": f"promotion-{promotion_id}",
                        "source_payload": case,
                        "summary": (
                            f"Promotion {promotion_id} performance summary: "
                            f"avg_ratio={case.get('avg_performance_ratio', 0)}"
                        ),
                    },
                )
            except Exception as exc:
                print(f"  [RAG Similarity] Failed to log promotion embedding metadata: {exc}")

    def _get_chroma_collection(self):
        if self._chroma_client is None:
            try:
                import chromadb  # type: ignore
            except Exception as exc:
                raise RuntimeError(
                    f"chromadb dependency missing: {exc}. Install and run Chroma server."
                ) from exc

            self._chroma_client = chromadb.HttpClient(
                host=config.RAG_CONFIG["chroma_host"],
                port=config.RAG_CONFIG["chroma_port"],
            )

        return self._chroma_client.get_or_create_collection(
            name=config.RAG_CONFIG["chroma_collection"]
        )

    @staticmethod
    def _build_query_text(state: Dict[str, Any]) -> str:
        inventory = state.get("inventory_data", {})
        weather = state.get("weather_data", {})
        social = state.get("social_data", {})
        competitors = state.get("competitor_data", [])
        return (
            f"sku_id={state.get('sku_id')} "
            f"store_id={state.get('store_id')} "
            f"category={inventory.get('category')} "
            f"stock_status={inventory.get('stock_status')} "
            f"avg_daily_sales={state.get('sell_through_rate', {}).get('avg_daily_sales')} "
            f"weather={weather.get('condition')} temp={weather.get('temperature_celsius')} "
            f"social_buzz={social.get('has_buzz')} "
            f"competitor_count={len(competitors)}"
        )

    def _upsert_cases_into_collection(self, collection, cases: List[Dict[str, Any]]) -> None:
        if not cases:
            return

        ids: List[str] = []
        docs: List[str] = []
        metas: List[Dict[str, Any]] = []

        for case in cases:
            promotion_id = case.get("promotion_id")
            if not promotion_id:
                continue
            ids.append(f"promotion-{promotion_id}")
            docs.append(
                " ".join(
                    [
                        f"promotion_type={case.get('promotion_type')}",
                        f"discount={case.get('discount_value')}",
                        f"margin={case.get('margin_percent')}",
                        f"avg_ratio={case.get('avg_performance_ratio')}",
                        f"status={case.get('status')}",
                        f"reason={case.get('reason')}",
                    ]
                )
            )
            metas.append(
                {
                    "promotion_id": int(promotion_id),
                    "sku_id": int(case.get("sku_id") or 0),
                    "store_id": int(case.get("store_id") or 0),
                    "avg_performance_ratio": float(case.get("avg_performance_ratio") or 0),
                }
            )

        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metas)

    def _format_chroma_result(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]

        output: List[Dict[str, Any]] = []
        for idx, value in enumerate(ids):
            output.append(
                {
                    "vector_id": value,
                    "distance": distances[idx] if idx < len(distances) else None,
                    "metadata": metadatas[idx] if idx < len(metadatas) else {},
                    "document": documents[idx] if idx < len(documents) else None,
                }
            )
        return output

    @staticmethod
    def _build_chroma_spinup_plan(error: str) -> List[str]:
        return [
            f"Vector retrieval unavailable: {error}",
            "Start a Chroma container on the shared network: `docker-compose --profile rag up -d chroma-db`.",
            "Ensure `ENABLE_RAG_SIMILARITY=true` and `CHROMA_HOST=chroma-db` in `.env`.",
            "Re-run the agent loop; embedding metadata is already being recorded for backfill.",
            f"Plan generated at {datetime.now().isoformat()}",
        ]

