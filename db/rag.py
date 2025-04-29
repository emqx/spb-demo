import os
import time
from dotenv import load_dotenv
import logging
from pathlib import Path
from tempfile import mkdtemp

from llama_index.core import SimpleDirectoryReader,StorageContext,VectorStoreIndex,Settings, load_index_from_storage
from llama_index.llms.siliconflow import SiliconFlow
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from ali_embedding import AliEmbeddings

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.readers.docling import DoclingReader
from llama_index.vector_stores.milvus import MilvusVectorStore

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
        
        if use_pg == "True" or use_pg == "true":
            use_pg = True
        else:
            use_pg = False

        if local_embedding:
            Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5",)
            self.__dimension = 768
            logging.info("Using local embedding model: BAAI/bge-base-en-v1.5")
        else:
            Settings.embed_model = AliEmbeddings(key=os.getenv("EMBEDDING_API_KEY"), base_url=os.getenv("EMBEDDING_API_BASE_URL"), model_name=os.getenv("EMBEDDING_MODEL_NAME"))
            self.__dimension = 1024
            logging.info("Using Ali embedding model")

        if use_pg:
            self.use_pg = True
            logging.info("Using PGVectorStore")
        else:
            self.use_pg = False
            logging.info("Using local VectorStore")
        self.engine = None
    
    @staticmethod
    def __create_pg_store(dimension: int) -> PGVectorStore:
        host = os.getenv("PGSQL_HOST", "localhost")
        port = os.getenv("PGSQL_PORT", 5432)
        user = os.getenv("PGSQL_USER", "emqx")
        password = os.getenv("PGSQL_PASSWORD", "public")
        
        vector_store = PGVectorStore.from_params(
            database="mydatabase",
            host=host,
            password=password,
            port=port,
            user=user,
            table_name="test_table",
            embed_dim= dimension,
            hnsw_kwargs={
                "hnsw_m": 16,
                "hnsw_ef_construction": 64,
                "hnsw_ef_search": 40,
                "hnsw_dist_method": "vector_cosine_ops",
            },
        )
        return vector_store
    
    def create_index_from_hybrid_chunks(self, path: str, store_uri: str):
        start_time = time.time()
        from docling.document_converter import DocumentConverter
        from docling.chunking import HybridChunker
        from llama_index.core.schema import Document

        doc = DocumentConverter().convert(path).document

        chunker = HybridChunker(max_tokens=500)
        chunks = list(chunker.chunk(dl_doc=doc))

        documents = [
            Document(
                text=chunk.meta.headings[0] + ': ' + chunk.text,
                metadata={
                    "headings": chunk.meta.headings,
                },
            ) for chunk in chunks
        ]
        vector_store = MilvusVectorStore(uri=store_uri, dim=self.__dimension, overwrite=True)
        if self.use_pg:
            vector_store = self.__create_pg_store(dimension=self.__dimension)
        index = VectorStoreIndex.from_documents(
            documents=documents,
            storage_context=StorageContext.from_defaults(vector_store=vector_store),
            embed_model=Settings.embed_model,
            show_progress=True,
        )
        self.engine = index.as_query_engine()
        end_time = time.time()
        logging.info(f"Index created from hybrid chunks in {end_time - start_time:.2f} seconds")
    
    def load_index_from_hybrid_chunks(self, store_uri: str):
        start_time = time.time()
        vector_store = MilvusVectorStore(uri=store_uri, dim=self.__dimension)
        if self.use_pg:
            vector_store = self.__create_pg_store(dimension=self.__dimension)
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=Settings.embed_model)
        self.engine = index.as_query_engine()
        end_time = time.time()
        logging.info(f"Index loaded from hybrid chunks in {end_time - start_time:.2f} seconds")
    
    def query(self, query: str):
        response = self.engine.query(query)
        return response
    
if __name__ == "__main__":
    project_path = os.path.abspath(os.path.dirname(__file__))
    logging.basicConfig(level=logging.INFO, filename=os.path.join(project_path, "../logs/rag.log"), filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")
    load_dotenv()
    rag = RAG()
    #rag.create_index_from_hybrid_chunks()
    rag.load_index_from_hybrid_chunks("./storage/zh_index.db")
    start_time = time.time()
    response = rag.query("解释 50156")
    end_time = time.time()
    logging.info(f"Query time: {end_time - start_time:.2f} seconds")
    logging.info(response.response.strip())



