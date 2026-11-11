"""Chapter 5 linked lists, ADTs, circular structures, and iterators."""

from __future__ import annotations

from typing import Callable, Generic, Iterator, TypeVar


T = TypeVar("T")
K = TypeVar("K")


def identity(value: T) -> T:
    return value


class Link(Generic[T]):
    """One node in a singly linked list."""

    def __init__(self, data: T, next_link: Link[T] | None = None) -> None:
        self._data = data
        self._next = next_link

    def get_data(self) -> T:
        return self._data

    def set_data(self, data: T) -> None:
        self._data = data

    def get_next(self) -> Link[T] | None:
        return self._next

    def set_next(self, link: Link[T] | None) -> None:
        if link is not None and not isinstance(link, Link):
            raise TypeError("next link must be Link or None")
        self._next = link

    def is_last(self) -> bool:
        return self._next is None

    def __str__(self) -> str:
        return str(self._data)


class LinkedListIterator(Generic[T]):
    """Explicit iterator with both has_more() and StopIteration support."""

    def __init__(self, linked_list: LinkedList[T]) -> None:
        self._list = linked_list
        self._next = linked_list.get_first_link()

    def next(self) -> T:
        if self._next is None:
            raise StopIteration
        item = self._next.get_data()
        self._next = self._next.get_next()
        return item

    def __next__(self) -> T:
        return self.next()

    def __iter__(self) -> LinkedListIterator[T]:
        return self

    def has_more(self) -> bool:
        return self._next is not None

    def current(self) -> T | None:
        return None if self._next is None else self._next.get_data()

    def reset(self) -> None:
        self._next = self._list.get_first_link()


class LinkedList(Generic[T]):
    """Unordered singly linked list with front insertion and keyed search."""

    def __init__(self) -> None:
        self._first: Link[T] | None = None

    def get_first_link(self) -> Link[T] | None:
        return self._first

    def set_first_link(self, link: Link[T] | None) -> None:
        if link is not None and not isinstance(link, Link):
            raise TypeError("first link must be Link or None")
        self._first = link

    # These aliases let list and link objects participate in the same
    # previous/current traversal pattern used by the chapter's delete method.
    def get_next(self) -> Link[T] | None:
        return self.get_first_link()

    def set_next(self, link: Link[T] | None) -> None:
        self.set_first_link(link)

    def is_empty(self) -> bool:
        return self._first is None

    def first(self) -> T:
        if self._first is None:
            raise IndexError("first item requested from empty linked list")
        return self._first.get_data()

    def insert(self, data: T) -> None:
        self._first = Link(data, self._first)

    def find(self, goal: K, key: Callable[[T], K] = identity) -> Link[T] | None:
        link = self._first
        while link is not None:
            if key(link.get_data()) == goal:
                return link
            link = link.get_next()
        return None

    def search(self, goal: K, key: Callable[[T], K] = identity) -> T | None:
        link = self.find(goal, key)
        return None if link is None else link.get_data()

    def insert_after(self, goal: K, new_data: T, key: Callable[[T], K] = identity) -> bool:
        link = self.find(goal, key)
        if link is None:
            return False
        link.set_next(Link(new_data, link.get_next()))
        return True

    def delete_first(self) -> T:
        if self._first is None:
            raise IndexError("delete from empty linked list")
        first = self._first
        self._first = first.get_next()
        first.set_next(None)
        return first.get_data()

    def delete(self, goal: K, key: Callable[[T], K] = identity) -> T:
        if self._first is None:
            raise IndexError("delete from empty linked list")
        if key(self._first.get_data()) == goal:
            return self.delete_first()

        previous = self._first
        current = previous.get_next()
        while current is not None:
            if key(current.get_data()) == goal:
                previous.set_next(current.get_next())
                current.set_next(None)
                return current.get_data()
            previous, current = current, current.get_next()
        raise KeyError(f"no linked-list item matches {goal!r}")

    def traverse(self, function: Callable[[T], object] = print) -> None:
        for item in self:
            function(item)

    def iterator(self) -> LinkedListIterator[T]:
        return LinkedListIterator(self)

    def __iter__(self) -> Iterator[T]:
        link = self._first
        while link is not None:
            yield link.get_data()
            link = link.get_next()

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __str__(self) -> str:
        return "[" + " > ".join(str(item) for item in self) + "]"


class DoubleEndedList(LinkedList[T]):
    """Singly linked list with O(1) insertion at both ends."""

    def __init__(self) -> None:
        super().__init__()
        self._last: Link[T] | None = None

    def set_first_link(self, link: Link[T] | None) -> None:
        super().set_first_link(link)
        if link is None or self._last is None:
            self._last = link

    def get_last_link(self) -> Link[T] | None:
        return self._last

    def insert(self, data: T) -> None:
        link = Link(data, self._first)
        self._first = link
        if self._last is None:
            self._last = link

    def last(self) -> T:
        if self._last is None:
            raise IndexError("last item requested from empty linked list")
        return self._last.get_data()

    def insert_last(self, data: T) -> None:
        link = Link(data)
        if self._last is None:
            self._first = self._last = link
        else:
            self._last.set_next(link)
            self._last = link

    def insert_after(self, goal: K, new_data: T, key: Callable[[T], K] = identity) -> bool:
        link = self.find(goal, key)
        if link is None:
            return False
        new_link = Link(new_data, link.get_next())
        link.set_next(new_link)
        if link is self._last:
            self._last = new_link
        return True

    def delete_first(self) -> T:
        item = super().delete_first()
        if self._first is None:
            self._last = None
        return item

    def delete(self, goal: K, key: Callable[[T], K] = identity) -> T:
        if self._first is None:
            raise IndexError("delete from empty linked list")
        if key(self._first.get_data()) == goal:
            return self.delete_first()

        previous = self._first
        current = previous.get_next()
        while current is not None:
            if key(current.get_data()) == goal:
                previous.set_next(current.get_next())
                if current is self._last:
                    self._last = previous
                current.set_next(None)
                return current.get_data()
            previous, current = current, current.get_next()
        raise KeyError(f"no linked-list item matches {goal!r}")


class OrderedList(LinkedList[T], Generic[T]):
    """Singly linked list that maintains ascending order by a fixed key."""

    def __init__(self, key: Callable[[T], object] = identity) -> None:
        super().__init__()
        self._key = key

    def find(self, goal: object) -> Link[T] | None:
        link = self._first
        while link is not None and self._key(link.get_data()) < goal:
            link = link.get_next()
        return link

    def search(self, goal: object) -> T | None:
        link = self.find(goal)
        if link is not None and self._key(link.get_data()) == goal:
            return link.get_data()
        return None

    def insert(self, data: T) -> None:
        goal = self._key(data)
        if self._first is None or self._key(self._first.get_data()) >= goal:
            self._first = Link(data, self._first)
            return
        previous = self._first
        while (
            previous.get_next() is not None
            and self._key(previous.get_next().get_data()) < goal
        ):
            previous = previous.get_next()  # type: ignore[assignment]
        previous.set_next(Link(data, previous.get_next()))

    def delete(self, goal: object) -> T:
        if self._first is None:
            raise IndexError("delete from empty ordered list")
        if self._key(self._first.get_data()) == goal:
            return self.delete_first()
        previous = self._first
        current = previous.get_next()
        while current is not None and self._key(current.get_data()) < goal:
            previous, current = current, current.get_next()
        if current is None or self._key(current.get_data()) != goal:
            raise KeyError(f"no ordered-list item matches {goal!r}")
        previous.set_next(current.get_next())
        current.set_next(None)
        return current.get_data()


class DoublyLink(Generic[T]):
    """Node with forward and backward references."""

    def __init__(
        self,
        data: T,
        next_link: DoublyLink[T] | None = None,
        previous: DoublyLink[T] | None = None,
    ) -> None:
        self._data = data
        self._next = next_link
        self._previous = previous

    def get_data(self) -> T:
        return self._data

    def get_next(self) -> DoublyLink[T] | None:
        return self._next

    def set_next(self, link: DoublyLink[T] | None) -> None:
        if link is not None and not isinstance(link, DoublyLink):
            raise TypeError("next link must be DoublyLink or None")
        self._next = link

    def get_previous(self) -> DoublyLink[T] | None:
        return self._previous

    def set_previous(self, link: DoublyLink[T] | None) -> None:
        if link is not None and not isinstance(link, DoublyLink):
            raise TypeError("previous link must be DoublyLink or None")
        self._previous = link

    def is_first(self) -> bool:
        return self._previous is None

    def is_last(self) -> bool:
        return self._next is None

    def __str__(self) -> str:
        return str(self._data)


class DoublyLinkedList(Generic[T]):
    """Double-ended doubly linked list with forward and backward traversal."""

    def __init__(self) -> None:
        self._first: DoublyLink[T] | None = None
        self._last: DoublyLink[T] | None = None

    def is_empty(self) -> bool:
        return self._first is None

    def first(self) -> T:
        if self._first is None:
            raise IndexError("first item requested from empty doubly linked list")
        return self._first.get_data()

    def last(self) -> T:
        if self._last is None:
            raise IndexError("last item requested from empty doubly linked list")
        return self._last.get_data()

    def find(self, goal: K, key: Callable[[T], K] = identity) -> DoublyLink[T] | None:
        link = self._first
        while link is not None:
            if key(link.get_data()) == goal:
                return link
            link = link.get_next()
        return None

    def search(self, goal: K, key: Callable[[T], K] = identity) -> T | None:
        link = self.find(goal, key)
        return None if link is None else link.get_data()

    def insert_first(self, data: T) -> None:
        link = DoublyLink(data, next_link=self._first)
        if self._first is None:
            self._first = self._last = link
        else:
            self._first.set_previous(link)
            self._first = link

    insert = insert_first

    def insert_last(self, data: T) -> None:
        link = DoublyLink(data, previous=self._last)
        if self._last is None:
            self._first = self._last = link
        else:
            self._last.set_next(link)
            self._last = link

    def delete_first(self) -> T:
        if self._first is None:
            raise IndexError("delete from empty doubly linked list")
        link = self._first
        self._first = link.get_next()
        if self._first is None:
            self._last = None
        else:
            self._first.set_previous(None)
        link.set_next(None)
        return link.get_data()

    def delete_last(self) -> T:
        if self._last is None:
            raise IndexError("delete from empty doubly linked list")
        link = self._last
        self._last = link.get_previous()
        if self._last is None:
            self._first = None
        else:
            self._last.set_next(None)
        link.set_previous(None)
        return link.get_data()

    def insert_after(self, goal: K, data: T, key: Callable[[T], K] = identity) -> bool:
        link = self.find(goal, key)
        if link is None:
            return False
        if link is self._last:
            self.insert_last(data)
            return True
        following = link.get_next()
        new_link = DoublyLink(data, next_link=following, previous=link)
        link.set_next(new_link)
        if following is not None:
            following.set_previous(new_link)
        return True

    def delete(self, goal: K, key: Callable[[T], K] = identity) -> T:
        link = self.find(goal, key)
        if link is None:
            raise KeyError(f"no doubly-linked item matches {goal!r}")
        if link is self._first:
            return self.delete_first()
        if link is self._last:
            return self.delete_last()
        previous = link.get_previous()
        following = link.get_next()
        if previous is not None:
            previous.set_next(following)
        if following is not None:
            following.set_previous(previous)
        link.set_previous(None)
        link.set_next(None)
        return link.get_data()

    def traverse_backwards(self, function: Callable[[T], object] = print) -> None:
        link = self._last
        while link is not None:
            function(link.get_data())
            link = link.get_previous()

    def __iter__(self) -> Iterator[T]:
        link = self._first
        while link is not None:
            yield link.get_data()
            link = link.get_next()

    def iter_reverse(self) -> Iterator[T]:
        link = self._last
        while link is not None:
            yield link.get_data()
            link = link.get_previous()

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __str__(self) -> str:
        return "[" + " > ".join(str(item) for item in self) + "]"


class CircularList(Generic[T]):
    """Singly linked circular list marked by a reference to its last link."""

    def __init__(self) -> None:
        self._last: Link[T] | None = None

    def is_empty(self) -> bool:
        return self._last is None

    def first(self) -> T:
        if self._last is None:
            raise IndexError("first item requested from empty circular list")
        first = self._last.get_next()
        if first is None:
            raise RuntimeError("circular-list invariant was broken")
        return first.get_data()

    def insert_first(self, data: T) -> None:
        if self._last is None:
            link = Link(data)
            link.set_next(link)
            self._last = link
            return
        first = self._last.get_next()
        link = Link(data, first)
        self._last.set_next(link)

    def insert_last(self, data: T) -> None:
        self.insert_first(data)
        if self._last is not None:
            next_link = self._last.get_next()
            if next_link is not None:
                self._last = next_link

    def delete_first(self) -> T:
        if self._last is None:
            raise IndexError("delete from empty circular list")
        first = self._last.get_next()
        if first is None:
            raise RuntimeError("circular-list invariant was broken")
        if first is self._last:
            self._last = None
        else:
            self._last.set_next(first.get_next())
        first.set_next(None)
        return first.get_data()

    def search(self, goal: K, key: Callable[[T], K] = identity) -> T | None:
        if self._last is None:
            return None
        first = self._last.get_next()
        current = first
        while current is not None:
            if key(current.get_data()) == goal:
                return current.get_data()
            current = current.get_next()
            if current is first:
                break
        return None

    def step(self) -> None:
        if self._last is not None:
            next_link = self._last.get_next()
            if next_link is not None:
                self._last = next_link

    def seek(self, goal: K, key: Callable[[T], K] = identity) -> bool:
        if self._last is None:
            return False
        first = self._last.get_next()
        current = first
        while current is not None:
            if key(current.get_data()) == goal:
                self._last = current
                return True
            current = current.get_next()
            if current is first:
                break
        return False

    def __iter__(self) -> Iterator[T]:
        if self._last is None:
            return
        first = self._last.get_next()
        current = first
        while current is not None:
            yield current.get_data()
            current = current.get_next()
            if current is first:
                break

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __str__(self) -> str:
        return "[" + " > ".join(str(item) for item in self) + "]"


class LinkStack(Generic[T]):
    """Stack ADT implemented by front operations on a linked list."""

    def __init__(self) -> None:
        self._list = LinkedList[T]()

    def push(self, item: T) -> None:
        self._list.insert(item)

    def pop(self) -> T:
        return self._list.delete_first()

    def peek(self) -> T:
        return self._list.first()

    def is_empty(self) -> bool:
        return self._list.is_empty()

    def __len__(self) -> int:
        return len(self._list)

    def __str__(self) -> str:
        return str(self._list)


class LinkQueue(Generic[T]):
    """Queue ADT implemented by a double-ended linked list."""

    def __init__(self) -> None:
        self._list = DoubleEndedList[T]()

    def insert(self, item: T) -> None:
        self._list.insert_last(item)

    enqueue = insert

    def remove(self) -> T:
        return self._list.delete_first()

    dequeue = remove

    def peek(self) -> T:
        return self._list.first()

    def is_empty(self) -> bool:
        return self._list.is_empty()

    def __len__(self) -> int:
        return len(self._list)

    def __iter__(self) -> Iterator[T]:
        return iter(self._list)

    def __str__(self) -> str:
        return str(self._list)


class LinkedDeque(Generic[T]):
    """Deque ADT implemented by a doubly linked list."""

    def __init__(self) -> None:
        self._list = DoublyLinkedList[T]()

    def insert_left(self, item: T) -> None:
        self._list.insert_first(item)

    def insert_right(self, item: T) -> None:
        self._list.insert_last(item)

    def remove_left(self) -> T:
        return self._list.delete_first()

    def remove_right(self) -> T:
        return self._list.delete_last()

    def peek_left(self) -> T:
        return self._list.first()

    def peek_right(self) -> T:
        return self._list.last()

    def is_empty(self) -> bool:
        return self._list.is_empty()

    def __len__(self) -> int:
        return len(self._list)

    def __iter__(self) -> Iterator[T]:
        return iter(self._list)

    def __str__(self) -> str:
        return str(self._list)


class LinkedPriorityQueue(Generic[T, K]):
    """Priority queue backed by an ascending ordered linked list."""

    def __init__(self, priority: Callable[[T], K] = identity) -> None:
        self._list = OrderedList(priority)

    def insert(self, item: T) -> None:
        self._list.insert(item)

    def remove(self) -> T:
        return self._list.delete_first()

    def peek(self) -> T:
        return self._list.first()

    def is_empty(self) -> bool:
        return self._list.is_empty()

    def __len__(self) -> int:
        return len(self._list)

    def __iter__(self) -> Iterator[T]:
        return iter(self._list)

    def __str__(self) -> str:
        return str(self._list)


class CircularStack(Generic[T]):
    """LIFO stack using front operations on a circular list."""

    def __init__(self) -> None:
        self._list = CircularList[T]()

    def push(self, item: T) -> None:
        self._list.insert_first(item)

    def pop(self) -> T:
        return self._list.delete_first()

    def peek(self) -> T:
        return self._list.first()

    def is_empty(self) -> bool:
        return self._list.is_empty()

    def __len__(self) -> int:
        return len(self._list)


class CircularQueueADT(Generic[T]):
    """FIFO queue using the same circular list implementation."""

    def __init__(self) -> None:
        self._list = CircularList[T]()

    def insert(self, item: T) -> None:
        self._list.insert_last(item)

    def remove(self) -> T:
        return self._list.delete_first()

    def peek(self) -> T:
        return self._list.first()

    def is_empty(self) -> bool:
        return self._list.is_empty()

    def __len__(self) -> int:
        return len(self._list)


class TwoLevelPriorityQueue(Generic[T, K]):
    """Priority queues grouped by key, preserving FIFO within each group."""

    def __init__(self) -> None:
        self._queues: dict[K, LinkQueue[T]] = {}

    def insert(self, item: T, priority: K) -> None:
        self._queues.setdefault(priority, LinkQueue()).insert(item)

    def remove(self, priority: K | None = None) -> T:
        if priority is None:
            available = [key for key, queue in self._queues.items() if not queue.is_empty()]
            if not available:
                raise IndexError("remove from empty priority queue")
            priority = min(available)
        queue = self._queues.get(priority)
        if queue is None or queue.is_empty():
            raise KeyError(f"priority {priority!r} has no queued items")
        item = queue.remove()
        if queue.is_empty():
            del self._queues[priority]
        return item

    def priorities(self) -> Iterator[K]:
        yield from sorted(self._queues)

    def __iter__(self) -> Iterator[T]:
        for priority in self.priorities():
            yield from self._queues[priority]

    def __len__(self) -> int:
        return sum(1 for _ in self)


class FibonacciIterator:
    """Bidirectional finite-prefix iterator over 1, 1, 2, 3, ... ."""

    def __init__(self) -> None:
        self._values = [1, 1]
        self._position = 0

    def next(self) -> int:
        if self._position >= len(self._values):
            self._values.append(self._values[-1] + self._values[-2])
        value = self._values[self._position]
        self._position += 1
        return value

    def previous(self) -> int:
        if self._position <= 0:
            raise StopIteration
        self._position -= 1
        return self._values[self._position]

    def __next__(self) -> int:
        return self.next()

    def __iter__(self) -> FibonacciIterator:
        return self


def chapter5_demo() -> str:
    """Return deterministic output for the Chapter 5 portfolio demo."""
    linked = LinkedList[int]()
    for value in (1, 4, 9):
        linked.insert(value)
    linked.insert_after(4, 16)

    ordered = OrderedList[int]()
    for value in (9, -2, 625, -64, 1):
        ordered.insert(value)

    doubly = DoublyLinkedList[str]()
    for value in ("A", "B", "C"):
        doubly.insert_last(value)

    circular = CircularList[str]()
    for value in ("Ada", "Don", "Tim"):
        circular.insert_last(value)
    circular.step()

    fibonacci = FibonacciIterator()
    first_five = [fibonacci.next() for _ in range(5)]
    repeated = fibonacci.previous()

    queue = LinkQueue[int]()
    for value in (1, 2, 3):
        queue.insert(value)

    return "\n".join(
        [
            "Chapter 5 Linked Lists Lab",
            "===========================",
            f"Singly linked list: {linked}",
            f"Ordered linked list: {ordered}",
            f"Doubly linked forward/backward: {list(doubly)} / {list(doubly.iter_reverse())}",
            f"Circular list after step: {circular}",
            f"Linked queue FIFO: {[queue.remove() for _ in range(len(queue))]}",
            f"Fibonacci iterator: {first_five}, previous() repeats {repeated}",
        ]
    )
