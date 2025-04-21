from typing import Any, List
from openai import OpenAI

from llama_index.core.embeddings import BaseEmbedding

class AliEmbeddings(BaseEmbedding):
    def __init__(self, key:str, base_url:str, model_name:str, **kwargs: Any,) -> None:
        super().__init__(**kwargs)
        self.model_name = model_name
        self._model: OpenAI = OpenAI(api_key=key, base_url=base_url)
        
    @classmethod
    def class_name(cls) -> str:
        return "Ali embedding."

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)

    def _get_query_embedding(self, query: str) -> List[float]:
        completion = self._model.embeddings.create(model=self.model_name, input=query, dimensions=1024, encoding_format="float")
        return completion.data[0].embedding

    def _get_text_embedding(self, text: str) -> List[float]:
        completion = self._model.embeddings.create(model=self.model_name, input=text, dimensions=1024, encoding_format="float")
        return completion.data[0].embedding

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        for text in texts:
            completion = self._model.embeddings.create(model=self.model_name, input=text, dimensions=1024, encoding_format="float")
            # Extract embedding from the response
            embedding_data = completion.data[0].embedding
            all_embeddings.append(embedding_data)
        return all_embeddings
