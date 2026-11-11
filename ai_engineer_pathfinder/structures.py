"""Small, explicit data structures used by the learning planner."""

from __future__ import annotations

from collections import deque
import heapq
from typing import Iterable, Iterator

from .models import Skill


class SkillCatalog:
    """Hash-table-backed collection supporting insertion, search, and traversal."""

    def __init__(self, skills: Iterable[Skill] = ()) -> None:
        self._records: dict[str, Skill] = {}
        for skill in skills:
            self.add(skill)

    def add(self, skill: Skill) -> None:
        """Insert a record using its stable skill ID as the key."""
        if skill.id in self._records:
            raise ValueError(f"duplicate skill key: {skill.id}")
        self._records[skill.id] = skill

    def get(self, skill_id: str) -> Skill:
        """Return one record or raise a useful lookup error."""
        try:
            return self._records[skill_id]
        except KeyError as exc:
            raise KeyError(f"unknown skill: {skill_id}") from exc

    def search(self, query: str) -> list[Skill]:
        """Traverse records and return case-insensitive field matches."""
        needle = query.casefold()
        return [
            skill
            for skill in self._records.values()
            if needle in skill.id.casefold()
            or needle in skill.title.casefold()
            or needle in skill.category.casefold()
            or needle in skill.description.casefold()
        ]

    def sorted_by_importance(self) -> list[Skill]:
        """Return a sorted traversal without changing the hash table."""
        return sorted(
            self._records.values(),
            key=lambda skill: (-skill.importance, skill.title.casefold()),
        )

    def __contains__(self, skill_id: str) -> bool:
        return skill_id in self._records

    def __iter__(self) -> Iterator[Skill]:
        return iter(self._records.values())

    def __len__(self) -> int:
        return len(self._records)


class SkillGraph:
    """Directed adjacency-list graph where edges point from prerequisite to skill."""

    def __init__(self, skills: Iterable[Skill] = ()) -> None:
        self._edges: dict[str, set[str]] = {}
        for skill in skills:
            self.add_skill(skill.id)
            for prerequisite in skill.prerequisites:
                self.add_edge(prerequisite, skill.id)

    def add_skill(self, skill_id: str) -> None:
        self._edges.setdefault(skill_id, set())

    def add_edge(self, prerequisite: str, skill_id: str) -> None:
        """Insert a directed prerequisite relationship."""
        self.add_skill(prerequisite)
        self.add_skill(skill_id)
        self._edges[prerequisite].add(skill_id)

    def neighbors(self, skill_id: str) -> tuple[str, ...]:
        return tuple(sorted(self._edges.get(skill_id, ())))

    def learning_path(self, starts: Iterable[str], target: str) -> list[str]:
        """Find the shortest dependency-forward path with breadth-first search."""
        start_nodes = tuple(dict.fromkeys(starts))
        if target in start_nodes:
            return [target]

        queue = deque(start_nodes)  # FIFO queue controls the BFS frontier.
        parent: dict[str, str | None] = {node: None for node in start_nodes}

        while queue:
            current = queue.popleft()
            for neighbor in self.neighbors(current):
                if neighbor in parent:
                    continue
                parent[neighbor] = current
                if neighbor == target:
                    return self._reconstruct(parent, target)
                queue.append(neighbor)

        return []

    @staticmethod
    def _reconstruct(parent: dict[str, str | None], target: str) -> list[str]:
        path: list[str] = []
        current: str | None = target
        while current is not None:
            path.append(current)
            current = parent[current]
        path.reverse()
        return path


class PriorityQueue:
    """Max-priority queue implemented with Python's min-heap primitive."""

    def __init__(self) -> None:
        self._items: list[tuple[int, str, str, Skill]] = []

    def push(self, skill: Skill) -> None:
        # Negating importance turns heapq's smallest-first behavior into
        # highest-priority-first behavior; the title breaks ties consistently.
        heapq.heappush(
            self._items,
            (-skill.importance, skill.title.casefold(), skill.id, skill),
        )

    def pop(self) -> Skill:
        if not self._items:
            raise IndexError("pop from empty skill priority queue")
        return heapq.heappop(self._items)[3]

    def __bool__(self) -> bool:
        return bool(self._items)
