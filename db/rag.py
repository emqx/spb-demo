import os
import time
from dotenv import load_dotenv
import logging

from llama_index.core import SimpleDirectoryReader,StorageContext,VectorStoreIndex,Settings
from llama_index.llms.siliconflow import SiliconFlow
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

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
        
        if use_pg == "True" or use_pg == "true":
            use_pg = True
        else:
            use_pg = False

        if local_embedding:
            self.__embedding = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5",)
            Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5",)
            self.__dimension = 768
        else:
            self.__embedding = AliEmbeddings(key=os.getenv("EMBEDDING_API_KEY"), base_url=os.getenv("EMBEDDING_API_BASE_URL"), model_name=os.getenv("EMBEDDING_MODEL_NAME"))
            Settings.embed_model = AliEmbeddings(key=os.getenv("EMBEDDING_API_KEY"), base_url=os.getenv("EMBEDDING_API_BASE_URL"), model_name=os.getenv("EMBEDDING_MODEL_NAME"))
            self.__dimension = 1024
        if use_pg:
            self.use_pg = True
        else:
            self.use_pg = False
        self.engine = None
        self.__index = None
        #self.__index = VectorStoreIndex.from_vector_store(vector_store=self.__store, embed_model=self.__embedding)
        #self.engine = self.__index.as_query_engine()
    
    def create_index(self):
        start_time = time.time()
        if self.use_pg:
            index = RAG.create_index_pg(self.__dimension)
            self.__store = self.__create_pg_store(dimension=self.__dimension)
            self.__index = index
        else:
            index = RAG.create_index_local()
            self.__store = index.storage_context.vector_store;
            self.__index = index
        self.engine = self.__index.as_query_engine()
        end_time = time.time()
        logging.info(f"Index created in {end_time - start_time:.2f} seconds, {self.use_pg}")
    
    def load_index(self):
        start_time = time.time()
        self.__index = VectorStoreIndex.from_vector_store(vector_store=self.__store, embed_model=self.__embedding)
        self.engine = self.__index.as_query_engine()
        end_time = time.time()
        logging.info(f"Index loaded in {end_time - start_time:.2f} seconds")
    
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
    
    @staticmethod
    def create_index_local() -> VectorStoreIndex:
        documents = SimpleDirectoryReader("./data").load_data()
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir="./storage")
        return index
    
    @staticmethod
    def create_index_pg(dim: int) -> VectorStoreIndex:
        local_embedding = os.getenv('EMBEDDING_LOCAL', True)
        dim = 1024
        if local_embedding:
            dim = 768
        else:
            dim = 1024
        storage_context = StorageContext.from_defaults(vector_store=RAG.__create_pg_store(dimension=dim))

        documents = SimpleDirectoryReader("./data").load_data()
        return VectorStoreIndex(documents, embed_model=Settings.embed_model, storage_context=storage_context, show_progress=True)

    def query(self, query: str):
        response = self.engine.query(query)
        return response

if __name__ == "__main__":
    project_path = os.path.abspath(os.path.dirname(__file__))
    logging.basicConfig(level=logging.INFO, filename=os.path.join(project_path, "../logs/rag.log"), filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")
    load_dotenv()
    rag = RAG()
    rag.create_index()
   # rag.load_index()
    start_time = time.time()
    #response = rag.query("What did the author do in college?")
    response = rag.query("What i worked?")
    end_time = time.time()
    logging.info(f"Query time: {end_time - start_time:.2f} seconds")
    print(response)