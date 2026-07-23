"""The adapter contract: the abstraction every data source must satisfy.

Kept deliberately small and capability-NEUTRAL. The base only promises
*discovery* — "what is this source, and what does it contain?" — because our
sources are diverse: a Google Sheet is tabular, a Google Doc is prose. Reading
capabilities (tabular rows vs document text) are introduced later as separate
capability interfaces, so no source is ever forced to implement an operation it
cannot support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class DataSourceAdapter(ABC):
    """Abstract base class every data-source adapter inherits from.

    A subclass that does not implement every abstract member cannot be
    instantiated — Python raises ``TypeError`` at construction time. That turns
    "I forgot to implement a method" from a subtle runtime bug into an immediate,
    obvious failure.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """A unique, stable identifier for this data source (e.g. ``"demo"``)."""

    @abstractmethod
    def list_resources(self) -> list[str]:
        """Return the names of the resources this source exposes.

        A "resource" is intentionally generic: it may be a spreadsheet tab, a
        database table, or a document. It is the addressable unit that a later
        read operation will target.
        """
