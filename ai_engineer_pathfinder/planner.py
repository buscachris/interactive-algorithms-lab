"""Application service that combines the Chapter 1 data structures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Skill
from .structures import PriorityQueue, SkillCatalog, SkillGraph


class Pathfinder:
    """Load, search, traverse, and prioritize an AI-engineering skill graph."""

    def __init__(self, skills: Iterable[Skill]) -> None:
        skills = tuple(skills)
        self.catalog = SkillCatalog(skills)
        self.graph = SkillGraph(skills)

    @classmethod
    def from_json(cls, path: Path) -> "Pathfinder":
        with path.open(encoding="utf-8") as stream:
            records = json.load(stream)
        return cls(Skill.from_dict(record) for record in records)

    def next_skills(self, completed: Iterable[str], limit: int = 5) -> list[Skill]:
        """Return eligible skills ordered by importance using a heap."""
        completed_set = set(completed)
        queue = PriorityQueue()
        for skill in self.catalog:
            if skill.id in completed_set:
                continue
            if set(skill.prerequisites).issubset(completed_set):
                queue.push(skill)

        result: list[Skill] = []
        while queue and len(result) < limit:
            result.append(queue.pop())
        return result

    def path_to(self, target: str, completed: Iterable[str]) -> list[Skill]:
        """Return a shortest prerequisite-forward path to a target skill."""
        self.catalog.get(target)  # Validate the key before graph traversal.
        path_ids = self.graph.learning_path(completed, target)
        return [self.catalog.get(skill_id) for skill_id in path_ids]

    def progress(self, completed: Iterable[str]) -> tuple[int, int, float]:
        completed_set = set(completed)
        total = len(self.catalog)
        finished = sum(skill.id in completed_set for skill in self.catalog)
        percentage = (finished / total * 100) if total else 0.0
        return finished, total, percentage


def default_data_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "skills.json"
