from typing import Dict, Type, List
from .base import ComparisonEngine
from ..utils import EngineNotFoundError, EngineUnavailableError

class EngineRegistry:
    _registry: Dict[str, Type[ComparisonEngine]] = {}
    _instances: Dict[str, ComparisonEngine] = {}

    @classmethod
    def register(cls, engine_class: Type[ComparisonEngine]) -> Type[ComparisonEngine]:
        cls._registry[engine_class.ENGINE_ID] = engine_class
        return engine_class

    @classmethod
    def get(cls, engine_id: str) -> ComparisonEngine:
        if engine_id not in cls._registry:
            raise EngineNotFoundError(
                f"Engine '{engine_id}' is not registered. Available: {list(cls._registry.keys())}"
            )

        if engine_id not in cls._instances:
            instance = cls._registry[engine_id]()
            if not instance.is_available():
                raise EngineUnavailableError(
                    f"Engine '{engine_id}' dependencies are missing. Check requirements."
                )
            cls._instances[engine_id] = instance

        return cls._instances[engine_id]

    @classmethod
    def get_default(cls) -> ComparisonEngine:
        preferred_ids = ["embedding_v1", "tfidf_v1"]
        for eid in preferred_ids:
            try:
                return cls.get(eid)
            except (EngineNotFoundError, EngineUnavailableError):
                continue
        raise EngineUnavailableError("No comparison engine is available.")

    @classmethod
    def list_available(cls) -> List[dict]:
        result = []
        for eid, ecls in cls._registry.items():
            try:
                instance = cls.get(eid)
                result.append({
                    "id": eid,
                    "name": instance.engine_name,
                    "available": True,
                    "capabilities": instance.capabilities,
                })
            except EngineUnavailableError:
                result.append({
                    "id": eid,
                    "name": getattr(ecls, 'ENGINE_NAME', str(ecls)),
                    "available": False,
                })
        return result
