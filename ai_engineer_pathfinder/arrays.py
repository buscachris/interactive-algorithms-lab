"""Chapter 2 array implementations and Big-O instrumentation.

The classes intentionally use explicit loops and an item count instead of
delegating everything to Python's higher-level list operations. That keeps the
array algorithms visible for study while still using a Python list as the
contiguous backing storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Iterator, TypeVar


T = TypeVar("T")
R = TypeVar("R")


@dataclass
class StepStats:
    """Small operation ledger used to compare algorithms experimentally."""

    comparisons: int = 0
    moves: int = 0

    @property
    def steps(self) -> int:
        return self.comparisons + self.moves


def identity(value: T) -> T:
    """Default record key: order the record itself."""
    return value


class Array(Generic[T]):
    """Fixed-capacity unordered array with a linear search."""

    def __init__(self, initial_size: int) -> None:
        if initial_size < 0:
            raise ValueError("initial_size must be non-negative")
        self.__a: list[T | None] = [None] * initial_size
        self.__n_items = 0
        self.last_stats = StepStats()

    @property
    def capacity(self) -> int:
        return len(self.__a)

    def __len__(self) -> int:
        return self.__n_items

    def __iter__(self) -> Iterator[T]:
        for index in range(self.__n_items):
            # The active prefix is populated by insert(), so this cast-free
            # local assignment keeps iteration readable for learners.
            value = self.__a[index]
            if value is not None:
                yield value

    def __str__(self) -> str:
        return str(list(self))

    def get(self, index: int) -> T | None:
        """Return an active item, or None when the index is out of bounds."""
        if 0 <= index < self.__n_items:
            return self.__a[index]  # type: ignore[return-value]
        return None

    def set(self, index: int, value: T) -> bool:
        """Replace an active cell and report whether the index was valid."""
        if 0 <= index < self.__n_items:
            self.__a[index] = value
            self.last_stats = StepStats(moves=1)
            return True
        self.last_stats = StepStats()
        return False

    def insert(self, item: T) -> None:
        """Insert at the first empty cell; duplicates are allowed."""
        if self.__n_items >= len(self.__a):
            raise OverflowError("array capacity exceeded")
        self.__a[self.__n_items] = item
        self.__n_items += 1
        self.last_stats = StepStats(moves=1)

    def find(self, item: T) -> int:
        """Return the first matching index, or -1 after a linear traversal."""
        stats = StepStats()
        for index in range(self.__n_items):
            stats.comparisons += 1
            if self.__a[index] == item:
                self.last_stats = stats
                return index
        self.last_stats = stats
        return -1

    def search(self, item: T) -> T | None:
        index = self.find(item)
        return self.get(index)

    def delete(self, item: T) -> bool:
        """Delete the first match and shift later items left to avoid holes."""
        index = self.find(item)
        stats = self.last_stats
        if index < 0:
            return False

        self.__n_items -= 1
        for position in range(index, self.__n_items):
            self.__a[position] = self.__a[position + 1]
            stats.moves += 1
        self.__a[self.__n_items] = None
        self.last_stats = stats
        return True

    def delete_rightmost(self) -> T | None:
        """Remove the final active cell in constant time."""
        if self.__n_items == 0:
            self.last_stats = StepStats()
            return None
        self.__n_items -= 1
        value = self.__a[self.__n_items]
        self.__a[self.__n_items] = None
        self.last_stats = StepStats(moves=1)
        return value  # type: ignore[return-value]

    def traverse(self, function: Callable[[T], object] = print) -> None:
        stats = StepStats()
        for item in self:
            function(item)
            stats.moves += 1
        self.last_stats = stats

    def get_max_num(self) -> int | float | None:
        """Return the greatest numeric item, ignoring non-numeric records."""
        maximum: int | float | None = None
        stats = StepStats()
        for item in self:
            stats.comparisons += 1
            if not isinstance(item, (int, float)):
                continue
            if maximum is None or item > maximum:
                maximum = item
        self.last_stats = stats
        return maximum

    def delete_max_num(self) -> int | float | None:
        """Remove and return the first item with the greatest numeric value."""
        maximum = self.get_max_num()
        if maximum is None:
            return None
        self.delete(maximum)
        return maximum

    def remove_dupes(self) -> int:
        """Remove duplicate values while preserving the first occurrence."""
        unique: list[T] = []
        removed = 0
        for item in self:
            if any(existing == item for existing in unique):
                removed += 1
            else:
                unique.append(item)

        original = list(self)
        self.__n_items = 0
        for item in unique:
            self.__a[self.__n_items] = item
            self.__n_items += 1
        for index in range(self.__n_items, len(self.__a)):
            self.__a[index] = None
        self.last_stats = StepStats(comparisons=len(original) * len(unique), moves=len(unique))
        return removed


class OrderedArray(Generic[T]):
    """Fixed-capacity ascending array with binary search and ordered inserts."""

    def __init__(self, initial_size: int) -> None:
        if initial_size < 0:
            raise ValueError("initial_size must be non-negative")
        self.__a: list[T | None] = [None] * initial_size
        self.__n_items = 0
        self.last_stats = StepStats()

    @property
    def capacity(self) -> int:
        return len(self.__a)

    def __len__(self) -> int:
        return self.__n_items

    def __iter__(self) -> Iterator[T]:
        for index in range(self.__n_items):
            value = self.__a[index]
            if value is not None:
                yield value

    def __str__(self) -> str:
        return str(list(self))

    def get(self, index: int) -> T:
        if 0 <= index < self.__n_items:
            return self.__a[index]  # type: ignore[return-value]
        raise IndexError(f"index {index} is out of range")

    def find(self, item: T) -> int:
        """Return an exact index or the insertion point using binary search."""
        low, high = 0, self.__n_items - 1
        stats = StepStats()
        while low <= high:
            middle = (low + high) // 2
            stats.comparisons += 1
            value = self.__a[middle]
            if value == item:
                # Continue left so duplicates have deterministic first-match
                # behavior instead of depending on the midpoint history.
                high = middle - 1
            elif value < item:  # type: ignore[operator]
                low = middle + 1
            else:
                high = middle - 1
        self.last_stats = stats
        return low

    def search(self, item: T) -> T | None:
        index = self.find(item)
        if index < self.__n_items and self.__a[index] == item:
            return self.__a[index]  # type: ignore[return-value]
        return None

    def insert(self, item: T) -> None:
        if self.__n_items >= len(self.__a):
            raise OverflowError("ordered array capacity exceeded")
        index = self.find(item)
        stats = self.last_stats
        for position in range(self.__n_items, index, -1):
            self.__a[position] = self.__a[position - 1]
            stats.moves += 1
        self.__a[index] = item
        self.__n_items += 1
        stats.moves += 1
        self.last_stats = stats

    def delete(self, item: T) -> bool:
        index = self.find(item)
        stats = self.last_stats
        if index >= self.__n_items or self.__a[index] != item:
            return False
        self.__n_items -= 1
        for position in range(index, self.__n_items):
            self.__a[position] = self.__a[position + 1]
            stats.moves += 1
        self.__a[self.__n_items] = None
        self.last_stats = stats
        return True

    def traverse(self, function: Callable[[T], object] = print) -> None:
        stats = StepStats()
        for item in self:
            function(item)
            stats.moves += 1
        self.last_stats = stats


class OrderedRecordArray(Generic[R]):
    """Expandable ordered array for records sorted by an immutable key function."""

    def __init__(
        self,
        initial_size: int,
        key: Callable[[R], T] = identity,
        growth_factor: int = 2,
    ) -> None:
        if initial_size < 0:
            raise ValueError("initial_size must be non-negative")
        if growth_factor < 2:
            raise ValueError("growth_factor must be at least 2")
        self.__a: list[R | None] = [None] * initial_size
        self.__n_items = 0
        self.__key = key
        self.__growth_factor = growth_factor
        self.last_stats = StepStats()

    @property
    def capacity(self) -> int:
        return len(self.__a)

    @property
    def key_function(self) -> Callable[[R], T]:
        return self.__key

    def __len__(self) -> int:
        return self.__n_items

    def __iter__(self) -> Iterator[R]:
        for index in range(self.__n_items):
            value = self.__a[index]
            if value is not None:
                yield value

    def __str__(self) -> str:
        return str(list(self))

    def get(self, index: int) -> R:
        if 0 <= index < self.__n_items:
            return self.__a[index]  # type: ignore[return-value]
        raise IndexError(f"index {index} is out of range")

    def _grow(self) -> None:
        new_capacity = max(1, len(self.__a) * self.__growth_factor)
        expanded: list[R | None] = [None] * new_capacity
        for index in range(self.__n_items):
            expanded[index] = self.__a[index]
        self.__a = expanded

    def find(self, key: T) -> int:
        """Return the lower-bound index for a record key with binary search."""
        low, high = 0, self.__n_items - 1
        stats = StepStats()
        while low <= high:
            middle = (low + high) // 2
            stats.comparisons += 1
            middle_key = self.__key(self.__a[middle])  # type: ignore[arg-type]
            if middle_key < key:
                low = middle + 1
            else:
                high = middle - 1
        self.last_stats = stats
        return low

    def search(self, key: T) -> R | None:
        index = self.find(key)
        if index < self.__n_items:
            record = self.__a[index]
            if record is not None and self.__key(record) == key:
                return record
        return None

    def insert(self, record: R) -> None:
        if self.__n_items >= len(self.__a):
            self._grow()
        index = self.find(self.__key(record))
        stats = self.last_stats
        for position in range(self.__n_items, index, -1):
            self.__a[position] = self.__a[position - 1]
            stats.moves += 1
        self.__a[index] = record
        self.__n_items += 1
        stats.moves += 1
        self.last_stats = stats

    def delete(self, record: R) -> bool:
        """Delete the exact record, even when several records share its key."""
        key = self.__key(record)
        index = self.find(key)
        stats = self.last_stats
        while index < self.__n_items:
            candidate = self.__a[index]
            stats.comparisons += 1
            if candidate is None or self.__key(candidate) != key:
                break
            if candidate == record:
                self.__n_items -= 1
                for position in range(index, self.__n_items):
                    self.__a[position] = self.__a[position + 1]
                    stats.moves += 1
                self.__a[self.__n_items] = None
                self.last_stats = stats
                return True
            index += 1
        self.last_stats = stats
        return False

    def merge(self, other: "OrderedRecordArray[R]") -> None:
        """Merge two sorted arrays in linear time when key functions match."""
        if self.__key is not other.__key:
            raise ValueError("ordered record arrays require identical key functions")

        left = list(self)
        right = list(other)
        merged: list[R] = []
        left_index = right_index = 0
        stats = StepStats()
        while left_index < len(left) and right_index < len(right):
            stats.comparisons += 1
            if self.__key(left[left_index]) <= self.__key(right[right_index]):
                merged.append(left[left_index])
                left_index += 1
            else:
                merged.append(right[right_index])
                right_index += 1
            stats.moves += 1
        merged.extend(left[left_index:])
        merged.extend(right[right_index:])
        stats.moves += (len(left) - left_index) + (len(right) - right_index)
        self.__a = [None] * max(len(self.__a), len(merged))
        self.__n_items = 0
        for record in merged:
            self.__a[self.__n_items] = record
            self.__n_items += 1
        self.last_stats = stats


def chapter2_demo() -> str:
    """Return a compact demonstration used by the CLI and portfolio README."""
    values = Array[int | str](8)
    for item in [77, 12, "model", 44, 12, 3]:
        values.insert(item)
    linear_index = values.find(44)
    linear_steps = values.last_stats.comparisons

    ordered = OrderedArray[int](8)
    for item in [77, 12, 44, 3, 12]:
        ordered.insert(item)
    binary_index = ordered.find(44)
    binary_steps = ordered.last_stats.comparisons

    key = lambda record: record[1]
    records = OrderedRecordArray[tuple[str, float]](2, key=key)
    for record in [("model-a", 3.1), ("model-b", 7.5), ("model-c", 3.1)]:
        records.insert(record)

    return "\n".join(
        [
            "Chapter 2 Array Lab",
            "====================",
            f"Unordered Array: {values}",
            f"Linear find(44): index={linear_index}, comparisons={linear_steps} (O(N))",
            f"Ordered Array: {ordered}",
            f"Binary find(44): index={binary_index}, comparisons={binary_steps} (O(log N))",
            f"OrderedRecordArray: {records}",
            f"Duplicate-key delete: {records.delete(('model-c', 3.1))} -> {records}",
            f"Expansion capacity: {records.capacity}",
        ]
    )
