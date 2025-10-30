---
description: "Python coding style guidelines following PEP 8 and modern best practices"
applyTo: "**/*.py"
---

# Python Coding Style Instructions

## Overview

This instruction file enforces Python coding standards based on PEP 8, type hints, and modern Python practices.

## Code Formatting

Use **Black** for automatic formatting and **Ruff** for linting.

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP"]
```

## Type Hints

**MANDATORY**: All public functions, methods, and classes must have type hints.

✅ **Good:**

```python
from typing import Optional, List
from uuid import UUID

def get_customer_orders(customer_id: UUID, limit: int = 10) -> List[Order]:
    """Retrieve customer orders with type hints."""
    pass

class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def create_order(self, customer_id: UUID) -> Order:
        return Order(id=uuid4(), customer_id=customer_id)
```

❌ **Bad:**

```python
def get_customer_orders(customer_id, limit=10):  # No type hints
    pass
```

## Naming Conventions

- **Classes**: PascalCase (`OrderService`, `CustomerRepository`)
- **Functions/Methods**: snake_case (`calculate_total`, `get_by_id`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private attributes**: Leading underscore (`_internal_state`)
- **Module names**: snake_case (`order_service.py`)

```python
# Good naming
class OrderProcessor:
    MAX_BATCH_SIZE = 100

    def __init__(self) -> None:
        self._cache: dict[str, Order] = {}

    def process_orders(self, orders: List[Order]) -> None:
        pass
```

## Docstrings

Use Google-style docstrings for public APIs:

```python
def calculate_discount(
    base_price: float,
    discount_percentage: float,
    customer_tier: str
) -> float:
    """Calculate discounted price based on customer tier.

    Args:
        base_price: The original price before discount
        discount_percentage: Discount percentage (0-100)
        customer_tier: Customer tier ("REGULAR", "PREMIUM", "VIP")

    Returns:
        The final price after applying discount

    Raises:
        ValueError: If discount_percentage is not between 0 and 100

    Example:
        >>> calculate_discount(100.0, 10.0, "PREMIUM")
        90.0
    """
    if not 0 <= discount_percentage <= 100:
        raise ValueError("Discount must be between 0 and 100")

    return base_price * (1 - discount_percentage / 100)
```

## Dataclasses and Pydantic

Prefer dataclasses for domain models and Pydantic for API schemas:

```python
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

# Domain model
@dataclass
class Order:
    id: UUID
    items: List[OrderItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

# API schema
class CreateOrderRequest(BaseModel):
    customer_id: str = Field(..., description="Customer UUID")
    items: List[OrderItemSchema] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "123e4567-e89b-12d3-a456-426614174000",
                "items": []
            }
        }
```

## Error Handling

Use specific exceptions and context managers:

```python
# Custom exceptions
class OrderError(Exception):
    """Base exception for order-related errors."""
    pass

class OrderNotFoundError(OrderError):
    """Raised when order is not found."""

    def __init__(self, order_id: UUID):
        self.order_id = order_id
        super().__init__(f"Order {order_id} not found")

# Context managers
from contextlib import contextmanager
from typing import Generator

@contextmanager
def transaction(session: Session) -> Generator[Session, None, None]:
    """Database transaction context manager."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Usage
with transaction(session) as tx:
    repository.save(order)
```

## Imports

Organize imports in this order:

1. Standard library
2. Third-party packages
3. Local application imports

Use isort or ruff for automatic sorting:

```python
# Standard library
import os
from collections.abc import AsyncGenerator  # Use collections.abc, not typing
from datetime import datetime
from uuid import UUID, uuid4

# Third-party
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import pytest

# Local
from domain.order import Order, OrderItem
from application.repositories import OrderRepository
from infrastructure.database import get_db_session
```

### Modern Python Import Rules (Python 3.9+)

**IMPORTANT**: Use modern type hints from `collections.abc` and built-in types:

✅ **Good (Modern Python 3.9+):**

```python
from collections.abc import AsyncGenerator, Callable, Iterable
from typing import Optional, TypeAlias

def get_items() -> list[str]:  # Use lowercase list, dict, set, tuple
    return ["item1", "item2"]

def process_data(items: dict[str, int]) -> None:  # Use dict[K, V] not Dict
    pass

async def stream_data() -> AsyncGenerator[str, None]:  # Import from collections.abc
    yield "data"
```

❌ **Bad (Deprecated):**

```python
from typing import List, Dict, AsyncGenerator  # Deprecated in Python 3.9+

def get_items() -> List[str]:  # Don't use typing.List
    return ["item1", "item2"]

def process_data(items: Dict[str, int]) -> None:  # Don't use typing.Dict
    pass
```

### Unused Import Prevention

**CRITICAL**: Remove unused imports immediately. Ruff will flag these as errors.

✅ **Good:**

```python
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def save(self, entity) -> None:
        pass
```

❌ **Bad:**

```python
from abc import ABC, abstractmethod  # Both imported but not used
from typing import Optional  # Imported but not used

# No code using these imports
```

**Exception**: `__init__.py` files can have unused imports for re-exporting:

```python
# src/domain/__init__.py
from .order import Order  # noqa: F401 - Re-exported for convenience
from .customer import Customer  # noqa: F401
```

## Function and Method Design

- **Keep functions small** (< 20 lines when possible)
- **Single responsibility**
- **Pure functions** when possible (no side effects)

```python
# Good: small, focused functions
def calculate_tax(amount: float, tax_rate: float) -> float:
    return amount * tax_rate

def calculate_total_with_tax(subtotal: float, tax_rate: float) -> float:
    tax = calculate_tax(subtotal, tax_rate)
    return subtotal + tax

# Bad: too many responsibilities
def process_order(order_data: dict) -> dict:
    # Validates, calculates, saves, sends email - too much!
    pass
```

## Type Aliases

Use type aliases for complex types:

```python
from typing import TypeAlias, Dict, List
from uuid import UUID

UserId: TypeAlias = UUID
OrderId: TypeAlias = UUID
ItemsMap: TypeAlias = Dict[str, List[OrderItem]]

def get_user_orders(user_id: UserId) -> List[Order]:
    pass
```

## Protocols (Interfaces)

Use Protocol for dependency inversion:

```python
from typing import Protocol, Optional

class Repository[T](Protocol):
    """Generic repository protocol."""

    def get_by_id(self, id: UUID) -> Optional[T]:
        ...

    def save(self, entity: T) -> None:
        ...

    def delete(self, id: UUID) -> None:
        ...

# Implementation
class SqlAlchemyOrderRepository:
    def get_by_id(self, id: UUID) -> Optional[Order]:
        # Concrete implementation
        pass
```

## Constants and Enums

Use Enums for related constants:

```python
from enum import Enum, auto

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PaymentMethod(Enum):
    CREDIT_CARD = auto()
    PAYPAL = auto()
    BANK_TRANSFER = auto()

# Usage
order.status = OrderStatus.CONFIRMED
```

## List/Dict Comprehensions

Use comprehensions for simple transformations:

```python
# Good: readable comprehension
active_orders = [order for order in orders if order.status == "ACTIVE"]

order_ids = [order.id for order in orders]

order_map = {order.id: order for order in orders}

# Bad: too complex, use regular loop
result = [
    process_order(order) if order.status == "PENDING"
    else update_order(order) if order.status == "ACTIVE"
    else cancel_order(order)
    for order in orders if order.customer_id in active_customers
]  # Too complex!
```

## f-strings

Use f-strings for string formatting:

```python
# Good
name = "John"
age = 30
message = f"Hello {name}, you are {age} years old"

# Debug formatting
value = 42
print(f"{value=}")  # Outputs: value=42

# Bad
message = "Hello %s, you are %d years old" % (name, age)  # Old style
message = "Hello {}, you are {} years old".format(name, age)  # Verbose
```

## Comments

Write self-documenting code. Use comments sparingly for "why", not "what":

```python
# Bad: obvious comment
# Get the customer by ID
customer = repository.get_by_id(customer_id)

# Good: explains reasoning
# Use cached value to avoid expensive database call during checkout
customer = self._cache.get(customer_id) or repository.get_by_id(customer_id)
```

## Line Length

Maximum 100 characters per line (configurable in black):

```python
# Good: readable within line limit
def create_order(
    customer_id: UUID,
    items: List[OrderItem],
    shipping_address: str,
    billing_address: str
) -> Order:
    pass

# Good: break long strings
message = (
    "This is a very long message that needs to be split "
    "across multiple lines for readability"
)
```

## Validation Checklist

- [ ] All public functions have type hints
- [ ] Code is formatted with Black
- [ ] Imports are organized (stdlib, third-party, local)
- [ ] Docstrings for public APIs
- [ ] Enums for related constants
- [ ] Dataclasses for data structures
- [ ] Type aliases for complex types
- [ ] No lines exceed 100 characters
- [ ] Meaningful variable names
- [ ] No commented-out code in commits

## Whitespace Rules

**CRITICAL**: No trailing whitespace on any line, including blank lines.

✅ **Good:**

```python
def my_function():
    """Docstring."""

    # Blank line above has no spaces
    return value
```

❌ **Bad:**

```python
def my_function():
    """Docstring."""

    # Blank line above has trailing spaces (invisible but causes errors)
    return value
```

**Tip**: Configure your editor to remove trailing whitespace on save.

## Unused Function Arguments

If a function parameter is required by an interface but not used, prefix it with underscore:

✅ **Good:**

```python
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan manager. App param required by FastAPI but not used."""
    yield

def handle_event(_event: dict[str, Any]) -> None:
    """Event handler. Event param required by protocol."""
    pass
```

❌ **Bad:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """App parameter not used - will trigger ARG001 error."""
    yield
```

## Union Types - Modern Syntax

Use `|` instead of `Union` for type unions (Python 3.10+):

✅ **Good (Python 3.10+):**

```python
def process(value: str | int) -> str | None:
    return str(value) if value else None

def get_user(id: str) -> User | None:
    return users.get(id)
```

❌ **Bad (Old syntax):**

```python
from typing import Union, Optional

def process(value: Union[str, int]) -> Optional[str]:
    return str(value) if value else None
```

## Common Ruff Errors to Avoid

### F401: Unused Import

Remove imports that aren't used in the file.

```python
# Bad
from abc import ABC, abstractmethod  # Both unused

# Repository interfaces will be defined here

# Good - only import when needed
# (no imports if nothing is implemented yet)
```

### UP035: Use collections.abc

Import from `collections.abc` instead of `typing` for collection types:

```python
# Good
from collections.abc import AsyncGenerator, Callable, Iterable, Iterator

# Bad
from typing import AsyncGenerator, Callable, Iterable, Iterator
```

### UP006/UP007: Modern Type Hints

Use built-in types and `|` operator:

```python
# Good
def func(items: list[str], mapping: dict[str, int]) -> str | None:
    pass

# Bad
from typing import List, Dict, Optional, Union

def func(items: List[str], mapping: Dict[str, int]) -> Optional[str]:
    pass
```

### W293: Blank Line Contains Whitespace

Ensure blank lines have no trailing spaces.

### ARG001: Unused Function Argument

Prefix unused arguments with underscore or use them.

## Pre-commit Validation

Before committing, always run:

```bash
# Fix auto-fixable issues
ruff check src/ tests/ --fix

# Verify all checks pass
ruff check src/ tests/

# Format code
black src/ tests/

# Type check
mypy src/
```

## Updated Validation Checklist

- [ ] All public functions have type hints
- [ ] Code is formatted with Black
- [ ] Imports are organized (stdlib, third-party, local)
- [ ] Use `collections.abc` for AsyncGenerator, Callable, etc.
- [ ] Use `list`, `dict`, `set`, `tuple` (lowercase) not `List`, `Dict`, etc.
- [ ] Use `|` for unions instead of `Union[]` (Python 3.10+)
- [ ] No unused imports (F401)
- [ ] No trailing whitespace on any lines (W293)
- [ ] Unused function arguments prefixed with `_` (ARG001)
- [ ] Docstrings for public APIs
- [ ] Enums for related constants
- [ ] Dataclasses for data structures
- [ ] Type aliases for complex types
- [ ] No lines exceed 100 characters
- [ ] Meaningful variable names
- [ ] No commented-out code in commits
- [ ] All ruff checks pass before committing

```

```
