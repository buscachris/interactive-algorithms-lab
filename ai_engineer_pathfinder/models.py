"""Domain records used by the Pathfinder application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Skill:
    """A roadmap record with a stable key and prerequisite fields."""

    id: str
    title: str
    category: str
    description: str
    prerequisites: tuple[str, ...] = field(default_factory=tuple)
    importance: int = 1
    status: str = "not_started"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Skill":
        """Convert a JSON record into a typed Python record."""
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            category=str(data["category"]),
            description=str(data["description"]),
            prerequisites=tuple(data.get("prerequisites", ())),
            importance=int(data.get("importance", 1)),
            status=str(data.get("status", "not_started")),
        )


@dataclass
class JobApplication:
    """A job-search record, included to demonstrate database-like records."""

    id: str
    company: str
    role: str
    status: str = "saved"
    priority: int = 1
