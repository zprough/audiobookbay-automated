from __future__ import annotations

from abc import ABC, abstractmethod

from agent.models.book_context import BookContext
from agent.models.decision import Decision


class BaseDecider(ABC):
    @abstractmethod
    def decide(self, context: BookContext) -> Decision:
        raise NotImplementedError