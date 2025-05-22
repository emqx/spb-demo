import os
import time
from dotenv import load_dotenv
import logging
from tempfile import mkdtemp

from llama_index.core import StorageContext, Settings 
from llama_index.llms.siliconflow import SiliconFlow
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterOperator,
)
from llama_index.vector_stores.milvus import MilvusVectorStore

from ali_embedding import AliEmbeddings

load_dotenv()
Settings.llm = SiliconFlow(api_key=os.getenv("SFAPI_KEY"),model=str(os.getenv("MODEL_NAME")),temperature=0,max_tokens=4000, timeout=180)
class RAG:
    def __init__(self):
        local_embedding = os.getenv('EMBEDDING_LOCAL')
        use_pg = os.getenv('EMBEDDING_PG')

        if local_embedding == "True" or local_embedding == "true":
            local_embedding = True
        else:
            local_embedding = False
        
        if local_embedding:
            Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5",)
            self.__dimension = 768
            self.__store_uri = "./storage/en_local.db"
            logging.info("Using local embedding model: BAAI/bge-base-en-v1.5")
        else:
            Settings.embed_model = AliEmbeddings(key=os.getenv("EMBEDDING_API_KEY"), base_url=os.getenv("EMBEDDING_API_BASE_URL"), model_name=os.getenv("EMBEDDING_MODEL_NAME"))
            self.__dimension = 1024
            self.__store_uri = "./storage/en_ali.db"
            logging.info("Using Ali embedding model")

        self.index = None
    
    def create_index_from_hybrid_chunks(self, path: str):
        start_time = time.time()
        from docling.document_converter import DocumentConverter
        from docling.chunking import HybridChunker
        from llama_index.core.schema import Document
        from llama_index.core import VectorStoreIndex 

        doc = DocumentConverter().convert(path).document

        chunker = HybridChunker(max_tokens=256)
        chunks = list(chunker.chunk(dl_doc=doc))

        for chunk in chunks:
            chunk.text = "\n".join([line for line in chunk.text.splitlines() if line.strip()])
            #logging.info(f"{chunk.meta}, {chunk.text}, {len(chunk.text)}")

        documents = [
            Document(
                text=chunk.meta.headings[0] + ': ' + chunk.text,
                metadata={
                    "headings": "".join(chunk.meta.headings),
                },
            ) for chunk in chunks
        ]
        vector_store = MilvusVectorStore(uri=self.__store_uri, dim=self.__dimension, overwrite=True)
        index = VectorStoreIndex.from_documents(
            documents=documents,
            storage_context=StorageContext.from_defaults(vector_store=vector_store),
            embed_model=Settings.embed_model,
            show_progress=True,
        )
        self.index = index
        end_time = time.time()
        logging.info(f"Index created from hybrid chunks in {end_time - start_time:.2f} seconds")
    
    def load_index_from_hybrid_chunks(self):
        from llama_index.core import VectorStoreIndex 

        start_time = time.time()
        vector_store = MilvusVectorStore(uri=self.__store_uri, dim=self.__dimension)
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=Settings.embed_model)
        self.index = index
        end_time = time.time()
        logging.info(f"Index loaded from hybrid chunks in {end_time - start_time:.2f} seconds")
    
    def query(self, query: str):
        from llama_index.core import get_response_synthesizer
        from llama_index.core.retrievers import VectorIndexRetriever
        from llama_index.core.query_engine import RetrieverQueryEngine
        from llama_index.core.postprocessor import SimilarityPostprocessor

        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=5,
            filters=MetadataFilters(
                filters=[MetadataFilter(
                    key="headings",
                    value=query,
                    operator=FilterOperator.TEXT_MATCH,
                )]
            ),
        )
        response_synthesizer = get_response_synthesizer()
        engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer,
            node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.5)],
        )

        response = engine.query(query)
        return response
    
if __name__ == "__main__":
    project_path = os.path.abspath(os.path.dirname(__file__))
    logging.basicConfig(level=logging.INFO, filename=os.path.join(project_path, "../logs/rag.log"), filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")
    load_dotenv()
    rag = RAG()
    #rag.create_index_from_hybrid_chunks("./data/3HAC066553-001_20250426182528.md")
    #rag.create_index_from_hybrid_chunks("./data/3HAC066553-010_20250426183500.md")
    rag.load_index_from_hybrid_chunks()
    start_time = time.time()
    response = rag.query("50515")
    end_time = time.time()
    logging.info(f"Query time: {end_time - start_time:.2f} seconds")
    logging.info(response.response)
    logging.info(response.metadata)
