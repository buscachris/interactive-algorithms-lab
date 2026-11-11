"""Chapter 4 stacks, queues, priority queues, and expression parsing."""

from __future__ import annotations

import operator
import re
from typing import Callable, Generic, Iterator, TypeVar


T = TypeVar("T")


class Stack(Generic[T]):
    """Fixed-capacity last-in, first-out (LIFO) storage."""

    def __init__(self, capacity: int) -> None:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        self._items: list[T | None] = [None] * capacity
        self._top = -1

    def push(self, item: T) -> None:
        if self.is_full():
            raise OverflowError("stack is full")
        self._top += 1
        self._items[self._top] = item

    def pop(self) -> T:
        if self.is_empty():
            raise IndexError("pop from empty stack")
        item = self._items[self._top]
        self._items[self._top] = None
        self._top -= 1
        return item  # type: ignore[return-value]

    def peek(self) -> T | None:
        return None if self.is_empty() else self._items[self._top]  # type: ignore[return-value]

    def is_empty(self) -> bool:
        return self._top < 0

    def is_full(self) -> bool:
        return self._top >= len(self._items) - 1

    def __len__(self) -> int:
        return self._top + 1

    def __iter__(self) -> Iterator[T]:
        for index in range(self._top + 1):
            yield self._items[index]  # type: ignore[misc]

    def __str__(self) -> str:
        return str(list(self))


class CircularQueue(Generic[T]):
    """Fixed-capacity first-in, first-out storage using a ring buffer."""

    def __init__(self, capacity: int) -> None:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        self._items: list[T | None] = [None] * capacity
        self._front = 0
        self._rear = -1
        self._count = 0

    def insert(self, item: T) -> None:
        if self.is_full():
            raise OverflowError("queue is full")
        if not self._items:
            raise OverflowError("queue capacity is zero")
        self._rear = (self._rear + 1) % len(self._items)
        self._items[self._rear] = item
        self._count += 1

    def remove(self) -> T:
        if self.is_empty():
            raise IndexError("remove from empty queue")
        item = self._items[self._front]
        self._items[self._front] = None
        self._front = (self._front + 1) % len(self._items)
        self._count -= 1
        return item  # type: ignore[return-value]

    def peek(self) -> T | None:
        return None if self.is_empty() else self._items[self._front]  # type: ignore[return-value]

    def is_empty(self) -> bool:
        return self._count == 0

    def is_full(self) -> bool:
        return self._count == len(self._items)

    def __len__(self) -> int:
        return self._count

    def __iter__(self) -> Iterator[T]:
        for offset in range(self._count):
            index = (self._front + offset) % len(self._items)
            yield self._items[index]  # type: ignore[misc]

    def __str__(self) -> str:
        return str(list(self))


class Deque(CircularQueue[T]):
    """Double-ended queue supporting insertion and removal at both ends."""

    def insert_left(self, item: T) -> None:
        if self.is_full():
            raise OverflowError("deque is full")
        if not self._items:
            raise OverflowError("deque capacity is zero")
        if self.is_empty():
            self._front = self._rear = 0
        else:
            self._front = (self._front - 1) % len(self._items)
        self._items[self._front] = item
        self._count += 1

    def insert_right(self, item: T) -> None:
        self.insert(item)

    def remove_left(self) -> T:
        return self.remove()

    def remove_right(self) -> T:
        if self.is_empty():
            raise IndexError("remove from empty deque")
        item = self._items[self._rear]
        self._items[self._rear] = None
        self._rear = (self._rear - 1) % len(self._items)
        self._count -= 1
        return item  # type: ignore[return-value]

    def peek_left(self) -> T | None:
        return self.peek()

    def peek_right(self) -> T | None:
        return None if self.is_empty() else self._items[self._rear]  # type: ignore[return-value]


class StablePriorityQueue(Generic[T]):
    """Fixed-capacity priority queue with FIFO ordering for equal priorities.

    Lower priority keys are removed first, matching the array implementation
    from the chapter. The internal array stores the highest-priority item at
    the right, so insertion is O(N) but removal and peek are O(1).
    """

    def __init__(self, capacity: int, priority: Callable[[T], object] | None = None) -> None:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        self._items: list[T] = []
        self._capacity = capacity
        self._priority = priority or (lambda item: item)

    def insert(self, item: T) -> None:
        if self.is_full():
            raise OverflowError("priority queue is full")
        index = len(self._items) - 1
        item_priority = self._priority(item)
        # Store keys in descending order. Shift equal or higher-priority keys
        # right so a newer equal-priority item lands before the older one;
        # popping from the right then returns the older item first.
        while index >= 0 and item_priority >= self._priority(self._items[index]):
            index -= 1
        self._items.insert(index + 1, item)

    def remove(self) -> T:
        if self.is_empty():
            raise IndexError("remove from empty priority queue")
        return self._items.pop()

    def peek(self) -> T | None:
        return None if self.is_empty() else self._items[-1]

    def is_empty(self) -> bool:
        return not self._items

    def is_full(self) -> bool:
        return len(self._items) >= self._capacity

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return reversed(self._items)

    def __str__(self) -> str:
        return str(list(self))


_TOKEN_PATTERN = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_]\w*)|(.))")
_OPERATORS = {"=": 0, "|": 1, "&": 2, "+": 3, "-": 3, "*": 4, "/": 4, "%": 4, "^": 5}


def tokenize(expression: str) -> list[str]:
    """Split an expression into numbers, variable names, and operators."""
    tokens: list[str] = []
    position = 0
    while position < len(expression):
        if expression[position:].strip() == "":
            break
        match = _TOKEN_PATTERN.match(expression, position)
        if match is None:
            raise ValueError(f"unexpected character at position {position}")
        number, name, symbol = match.groups()
        tokens.append(number or name or symbol)
        position = match.end()
    return tokens


def infix_to_postfix(expression: str) -> str:
    """Translate an infix expression to readable postfix notation."""
    output: list[str] = []
    operators = Stack[str](max(1, len(expression)))

    for token in tokenize(expression):
        if token[0].isdigit() or token[0].isalpha() or token[0] == "_":
            output.append(token)
        elif token == "(":
            operators.push(token)
        elif token == ")":
            while not operators.is_empty() and operators.peek() != "(":
                output.append(operators.pop())
            if operators.is_empty():
                raise ValueError("unmatched closing parenthesis")
            operators.pop()
        elif token in _OPERATORS:
            while not operators.is_empty() and operators.peek() != "(":
                top = operators.peek()
                if top is None or _OPERATORS[top] < _OPERATORS[token]:
                    break
                output.append(operators.pop())
            operators.push(token)
        else:
            raise ValueError(f"unsupported token: {token}")

    while not operators.is_empty():
        token = operators.pop()
        if token == "(":
            raise ValueError("unmatched opening parenthesis")
        output.append(token)
    return " ".join(output)


def _number(token: str) -> int | float:
    return float(token) if "." in token else int(token)


def evaluate_postfix(postfix: str, variables: dict[str, int | float] | None = None) -> tuple[int | float, dict[str, int | float]]:
    """Evaluate postfix arithmetic and return the result plus variable state."""
    values: Stack[int | float | str] = Stack(max(1, len(postfix.split())))
    bindings = {} if variables is None else variables

    def resolve(value: int | float | str) -> int | float:
        if isinstance(value, str):
            if value not in bindings:
                raise ValueError(f"variable {value!r} has not been assigned")
            return bindings[value]
        return value

    operations: dict[str, Callable[[int | float, int | float], int | float]] = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
        "%": operator.mod,
        "^": operator.xor,
        "|": operator.or_,
        "&": operator.and_,
    }

    for token in postfix.split():
        if token[0].isdigit():
            values.push(_number(token))
        elif token[0].isalpha() or token[0] == "_":
            values.push(token)
        elif token == "=":
            right = values.pop()
            left = values.pop()
            if not isinstance(left, str):
                raise ValueError("left side of assignment must be a variable")
            bindings[left] = resolve(right)
            values.push(bindings[left])
        elif token in operations:
            right = resolve(values.pop())
            left = resolve(values.pop())
            values.push(operations[token](left, right))
        else:
            raise ValueError(f"unsupported postfix token: {token}")

    if len(values) != 1:
        raise ValueError("expression did not reduce to one result")
    return resolve(values.pop()), bindings


def evaluate_expression(expression: str) -> tuple[str, int | float, dict[str, int | float]]:
    """Translate and evaluate one infix expression."""
    postfix = infix_to_postfix(expression)
    result, variables = evaluate_postfix(postfix)
    return postfix, result, variables


def check_delimiters(expression: str) -> tuple[bool, list[str]]:
    """Check matching parentheses, brackets, and braces with a stack."""
    stack = Stack[str](max(1, len(expression)))
    matching = {")": "(", "]": "[", "}": "{",
    }
    errors: list[str] = []
    for position, character in enumerate(expression):
        if character in "([{":
            stack.push(character)
        elif character in matching:
            if stack.is_empty():
                errors.append(f"{character} at position {position} has no opener")
            elif stack.pop() != matching[character]:
                errors.append(f"{character} at position {position} does not match the opener")
    if not stack.is_empty():
        errors.append(f"missing closers for {list(stack)}")
    return not errors, errors


def is_palindrome(text: str) -> bool:
    """Return whether letters and digits read the same in both directions."""
    normalized = "".join(character.casefold() for character in text if character.isalnum())
    stack = Stack[str](len(normalized))
    for character in normalized:
        stack.push(character)
    return normalized == "".join(stack.pop() for _ in range(len(stack)))


def chapter4_demo() -> str:
    """Return deterministic output for the Chapter 4 portfolio demo."""
    stack = Stack[str](6)
    for word in ("May", "the", "force", "be", "with", "you"):
        stack.push(word)
    reversed_words = []
    while not stack.is_empty():
        reversed_words.append(stack.pop())

    queue = CircularQueue[str](4)
    for item in ("A", "B", "C"):
        queue.insert(item)
    queue.remove()
    queue.insert("D")
    queue.insert("E")

    priority = StablePriorityQueue[tuple[int, str]](6, priority=lambda record: record[0])
    for record in ((1, "Don"), (0, "Ada"), (1, "Len"), (0, "Joe")):
        priority.insert(record)
    priority_order = [priority.remove() for _ in range(len(priority))]

    expression = "(A = 3 + 4 * 5) + (B = 7 * 6) + B / A"
    postfix, result, variables = evaluate_expression(expression)
    return "\n".join(
        [
            "Chapter 4 Stacks and Queues Lab",
            "================================",
            f"Stack pop order: {reversed_words}",
            f"Circular queue after wraparound: {list(queue)}",
            f"Priority queue removal order: {priority_order}",
            f"Postfix: {postfix}",
            f"Expression result: {result}",
            f"Variables: {variables}",
        ]
    )
