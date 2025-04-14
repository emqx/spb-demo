from llama_index.core import SimpleDirectoryReader,StorageContext,VectorStoreIndex,Settings
from llama_index.core.node_parser import JSONNodeParser
from llama_index.llms.siliconflow import SiliconFlow
from utils import AliEmbeddings
from llama_index.vector_stores.postgres import PGVectorStore
import os
from dotenv import load_dotenv
from sqlalchemy import make_url
# import psycopg2

load_dotenv()

Settings.llm = SiliconFlow(api_key=os.getenv("SF_API_KEY"),model=os.getenv("MODEL_NAME"),temperature=0,max_tokens=4000, timeout=180)
embedding = AliEmbeddings(key=os.getenv("EMBEDDING_API_KEY"), base_url=os.getenv("EMBEDDING_API_BASE_URL"), model_name=os.getenv("EMBEDDING_MODEL_NAME"))

def create_pg_store()->PGVectorStore:
    db_name=os.getenv("PGSQL_DB")
    connection_string=f'{os.getenv("PGSQL_CONN")}/{db_name}'
    # print(connection_string)
    # conn = psycopg2.connect(connection_string)
    # conn.autocommit = True
    # with conn.cursor() as c:
    #     c.execute(f"DROP DATABASE IF EXISTS {db_name}")
    #     c.execute(f"CREATE DATABASE {db_name}")

    url = make_url(connection_string)
    vector_store = PGVectorStore.from_params(
        database=db_name,
        host=url.host,
        password=url.password,
        port=url.port,
        user=url.username,
        table_name=os.getenv("PGSQL_TABLE"),
        embed_dim=1024,  # openai embedding dimension
        hnsw_kwargs={
            "hnsw_m": 16,
            "hnsw_ef_construction": 64,
            "hnsw_ef_search": 40,
            "hnsw_dist_method": "vector_cosine_ops",
        },
    )
    return vector_store

def create_index()->VectorStoreIndex:
    vector_store = create_pg_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    documents = SimpleDirectoryReader("./data").load_data()
    parser = JSONNodeParser()
    nodes = parser.get_nodes_from_documents(documents)

    return VectorStoreIndex(nodes, embed_model=embedding, storage_context=storage_context, show_progress=True)

def query_index()->VectorStoreIndex:
    vector_store = create_pg_store()
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=embedding)
    query_engine = index.as_query_engine()
    return query_engine

# query_engine = vector_index.as_query_engine(streaming=True)
# response.print_response_stream()

def main():
    # query_engine = create_index().as_query_engine()
    query_engine = query_index()
    response = query_engine.query("平均速度")
    print(response)

if __name__ == "__main__":
    main()
