from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from app.config import settings
from app.core.rules.models import RuleProfile


class ProfileLoader:
    """Loads and validates campus formatting rule profiles."""

    def __init__(self, profiles_dir: Path | None = None) -> None:
        self.profiles_dir = profiles_dir or settings.profiles_dir
        self.schema_path = self.profiles_dir / "schema" / "profile.schema.json"
        self._schema: dict[str, Any] | None = None
        self._cache: dict[str, RuleProfile] = {}

    @property
    def schema(self) -> dict[str, Any]:
        if self._schema is None:
            if not self.schema_path.exists():
                raise FileNotFoundError(f"Schema not found at {self.schema_path}")
            with open(self.schema_path, encoding="utf-8") as f:
                self._schema = json.load(f)
        return self._schema

    def validate_raw(self, data: dict[str, Any]) -> None:
        """Validates raw JSON against profile.schema.json."""
        jsonschema.validate(instance=data, schema=self.schema)

    def load_raw(self, profile_id: str) -> dict[str, Any]:
        """Loads raw JSON dict from profile_id.json."""
        file_path = self.profiles_dir / f"{profile_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Profile '{profile_id}' not found in {self.profiles_dir}")
        with open(file_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deeply merges two dicts where override takes precedence."""
        merged = base.copy()
        for k, v in override.items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = self._deep_merge(merged[k], v)
            else:
                merged[k] = v
        return merged

    def load(self, profile_id: str) -> RuleProfile:
        """Loads, merges inheritance, validates against JSON Schema, and returns RuleProfile."""
        if profile_id in self._cache:
            return self._cache[profile_id]

        data = self.load_raw(profile_id)

        # Handle 'extends'
        parent_id = data.get("extends")
        if parent_id:
            # Ensure parent is valid and merge raw dicts so None defaults do not break schema validation
            _ = self.load(parent_id)
            parent_dict = self.load_raw(parent_id)
            data = self._deep_merge(parent_dict, data)

        # Validate merged profile against JSON Schema
        self.validate_raw(data)

        profile = RuleProfile.model_validate(data)
        self._cache[profile_id] = profile
        return profile

    def list_available_profiles(self) -> list[dict[str, Any]]:
        """Returns metadata for all valid profiles in `profiles_dir`."""
        results: list[dict[str, Any]] = []
        if not self.profiles_dir.exists():
            return results

        for path in sorted(self.profiles_dir.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    content = json.load(f)
                pid = content.get("profile_id")
                if not pid:
                    continue
                validated = self.load(pid)
                results.append(
                    {
                        "profile_id": validated.profile_id,
                        "name": validated.name,
                        "version": validated.version,
                        "language": validated.language,
                        "source": validated.source,
                    }
                )
            except Exception:
                # Invalid profiles are excluded per FR-02
                continue

        return results


profile_loader = ProfileLoader()
