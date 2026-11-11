"""Chapter 3 simple sorting algorithms.

The implementation keeps the elementary algorithms explicit so their nested
loops, invariants, and operation counts can be studied.  ``SortableArray``
reuses the fixed-capacity array from Chapter 2 and adds bubble sort, selection
sort, insertion sort, and a few related exercises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from .arrays import Array


T = TypeVar("T")


@dataclass
class SortStats:
    """Operation counts for one sort or array transformation."""

    comparisons: int = 0
    copies: int = 0
    swaps: int = 0
    passes: int = 0

    @property
    def steps(self) -> int:
        """Return a simple total for comparing runs of the same algorithm."""
        return self.comparisons + self.copies + self.swaps


class SortableArray(Array[T]):
    """A Chapter 2 array extended with Chapter 3 sorting algorithms."""

    def _value(self, index: int) -> T:
        value = self.get(index)
        if value is None:
            raise IndexError(f"index {index} does not contain an active item")
        return value

    def swap(self, first: int, second: int, stats: SortStats | None = None) -> None:
        """Swap two active cells and optionally record one high-level swap."""
        if not (0 <= first < len(self) and 0 <= second < len(self)):
            raise IndexError("swap indices must refer to active items")
        left = self._value(first)
        right = self._value(second)
        super().set(first, right)
        super().set(second, left)
        if stats is not None:
            stats.swaps += 1

    def bubble_sort(self) -> SortStats:
        """Sort by repeatedly swapping adjacent out-of-order values."""
        stats = SortStats()
        for last in range(len(self) - 1, 0, -1):
            stats.passes += 1
            for inner in range(last):
                stats.comparisons += 1
                if self._value(inner) > self._value(inner + 1):
                    self.swap(inner, inner + 1, stats)
        self.last_stats = stats
        return stats

    def selection_sort(self) -> SortStats:
        """Sort by selecting the minimum remaining value on each pass."""
        stats = SortStats()
        for outer in range(len(self) - 1):
            stats.passes += 1
            minimum = outer
            for inner in range(outer + 1, len(self)):
                stats.comparisons += 1
                if self._value(inner) < self._value(minimum):
                    minimum = inner
            # This intentionally counts the self-swap, matching the simple
            # algorithm in the chapter before optional optimization.
            self.swap(outer, minimum, stats)
        self.last_stats = stats
        return stats

    def insertion_sort(self) -> SortStats:
        """Sort by inserting each marked value into the sorted prefix."""
        stats = SortStats()
        for outer in range(1, len(self)):
            stats.passes += 1
            marked = self._value(outer)
            stats.copies += 1  # Copy the marked value to temporary storage.
            inner = outer

            while inner > 0:
                stats.comparisons += 1
                previous = self._value(inner - 1)
                if not marked < previous:
                    break
                super().set(inner, previous)
                stats.copies += 1
                inner -= 1

            super().set(inner, marked)
            stats.copies += 1
        self.last_stats = stats
        return stats

    def odd_even_sort(self) -> SortStats:
        """Sort through alternating odd-index and even-index pair passes."""
        stats = SortStats()
        swapped = True
        while swapped:
            swapped = False
            stats.passes += 1

            for start in (1, 0):
                for index in range(start, len(self) - 1, 2):
                    stats.comparisons += 1
                    if self._value(index) > self._value(index + 1):
                        self.swap(index, index + 1, stats)
                        swapped = True
        self.last_stats = stats
        return stats

    def deduplicate(self) -> int:
        """Remove adjacent duplicates from a sorted array in O(N) time.

        The caller must sort the array first.  Each unique value is written at
        most once, and trailing duplicate cells are removed from the right so
        no remaining item is shifted repeatedly.
        """
        stats = SortStats()
        values = list(self)
        if not values:
            self.last_stats = stats
            return 0

        write = 0
        last_unique = values[0]
        for read in range(1, len(values)):
            stats.comparisons += 1
            if values[read] == last_unique:
                continue
            write += 1
            last_unique = values[read]
            if write != read:
                super().set(write, values[read])
                stats.copies += 1

        removed = len(values) - (write + 1)
        for _ in range(removed):
            self.delete_rightmost()
            stats.copies += 1

        self.last_stats = stats
        return removed


def _load(values: list[int]) -> SortableArray[int]:
    array = SortableArray[int](len(values))
    for value in values:
        array.insert(value)
    return array


def chapter3_demo() -> str:
    """Return deterministic output comparing the three simple sorts."""
    values = [77, 94, 59, 85, 61, 46, 62, 17]
    lines = ["Chapter 3 Simple Sorting Lab", "=============================", f"Input: {values}"]

    for name, method_name in (
        ("Bubble sort", "bubble_sort"),
        ("Selection sort", "selection_sort"),
        ("Insertion sort", "insertion_sort"),
    ):
        array = _load(values)
        stats = getattr(array, method_name)()
        lines.append(
            f"{name}: {list(array)} | comparisons={stats.comparisons}, "
            f"copies={stats.copies}, swaps={stats.swaps}, O(N^2)"
        )

    nearly_sorted = _load([1, 2, 3, 5, 4, 6, 7])
    stats = nearly_sorted.insertion_sort()
    lines.append(
        f"Nearly sorted insertion sort: comparisons={stats.comparisons}, "
        f"copies={stats.copies}"
    )
    return "\n".join(lines)
