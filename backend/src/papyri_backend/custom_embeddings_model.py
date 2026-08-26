from langchain.embeddings import Embeddings
import os
from pathlib import Path
from typing import Any


class CustomEmbeddings(Embeddings):
    @classmethod
    def from_config(cls, config: str) -> CustomEmbeddings: ...

    def __init__(
        self,
    ): ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed search docs.

        Args:
            texts: List of text to embed.

        Returns:
            List of embeddings.
        """

    def embed_query(self, text: str) -> list[float]:
        """Embed query text.

        Args:
            text: Text to embed.

        Returns:
            Embedding.
        """
