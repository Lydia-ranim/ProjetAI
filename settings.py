"""Application configuration for the LYHLYH FastAPI backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_env_file(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "LYHLYH Transit API")
    app_version: str = os.getenv("APP_VERSION", "1.1.0")
    data_dir: str = str((BASE_DIR / os.getenv("DATA_DIR", "data")).resolve()) if not Path(os.getenv("DATA_DIR", "data")).is_absolute() else os.getenv("DATA_DIR", str(BASE_DIR / "data"))
    google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    google_maps_region: str = os.getenv("GOOGLE_MAPS_REGION", "DZ")
    google_maps_language: str = os.getenv("GOOGLE_MAPS_LANGUAGE", "fr")
    cors_origins: tuple[str, ...] = tuple(
        x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()
    )
    polyline_simplify_tolerance: float = float(
        os.getenv("POLYLINE_SIMPLIFY_TOLERANCE", "0.00008")
    )
    max_polyline_points: int = int(os.getenv("MAX_POLYLINE_POINTS", "600"))
    nearest_stop_cache_size: int = int(os.getenv("NEAREST_STOP_CACHE_SIZE", "512"))
    google_visual_directions: bool = os.getenv("GOOGLE_VISUAL_DIRECTIONS", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    @property
    def google_maps_enabled(self) -> bool:
        return bool(self.google_maps_api_key)


settings = Settings()
