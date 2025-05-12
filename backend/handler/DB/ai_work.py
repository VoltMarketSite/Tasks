import time, os, sqlite3, tqdm, torch
import asyncio, httpx, chromadb
from chromadb.config import Settings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai.embeddings import OpenAIEmbeddings
from loguru import logger
from langchain_chroma import Chroma
 
PATH = os.path.dirname(os.path.abspath(__file__))
# API_URL = "https://api.proxyapi.ru/openai/v1"
API_KEY = "sk-9rfsKOTg9ThEaqO0Cp4BMJAmFBH8DTLF"
API_URL = "https://api.proxyapi.ru/openai/v1/embeddings"
MODEL = "text-embedding-3-small"

CHROMA_PATH = f"{PATH}\\volt_chroma_db"
COLLECTION_NAME = "volt_data"

def db2json():
    conn = sqlite3.connect(f"{PATH}\\base.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM base_volt LIMIT 5000")
    list_base: list[dict] = []

    for i in tqdm.tqdm(cur.fetchall()):
        list_base.append({"text": i[1], "metadata": {"id": i[0], "article": "" if i[2] is None else i[2], "manufactor": "" if i[3] is None else i[3]}})
    
    conn.close()
    
    return list_base

async def generate_chroma_db_async():
    SHOP_DATA = db2json()
    start_time = time.time()

    logger.info("Загрузка модели эмбеддингов...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/BAAI/bge-m3",
        model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    # embeddings = OpenAIEmbeddings(
    #     model="text-embedding-3-small",
    #     api_key="sk-9rfsKOTg9ThEaqO0Cp4BMJAmFBH8DTLF",
    #     base_url=API_URL
    # )
    logger.info(f"Модель загружена за {time.time() - start_time:.2f} сек")

    logger.info("Инициализация пустой Chroma DB...")
    chroma_db = Chroma(
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME
    )

    logger.info("Добавление документов с прогрессом...")

    async def process_item(item):
        await asyncio.to_thread(chroma_db.add_texts,
            texts=[item["text"]],
            metadatas=[item["metadata"]],
            ids=[str(item["metadata"]["id"])]
        )

    for item in tqdm.tqdm(SHOP_DATA, desc="Создание базы", unit="товар"):
        await process_item(item)

    await asyncio.to_thread(chroma_db.persist)

    logger.success(f"Chroma DB создана за {time.time() - start_time:.2f} сек")
    return chroma_db


def generate_chroma_db():
    SHOP_DATA = db2json()
    try:
        start_time = time.time()
        
        logger.info("Загрузка модели эмбеддингов...")
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info(f"Модель загружена за {time.time() - start_time:.2f} сек")
        
        logger.info("Создание Chroma DB...")
        # chroma_db = Chroma.from_texts(
        #     texts=[item["text"] for item in SHOP_DATA],
        #     embedding=embeddings,
        #     ids=[str(item["metadata"]["id"]) for item in SHOP_DATA],
        #     metadatas=[item["metadata"] for item in SHOP_DATA],
        #     persist_directory=CHROMA_PATH,
        #     collection_name=COLLECTION_NAME,
        # )
        chroma_db = Chroma(
            embedding_function=embeddings,
            persist_directory=CHROMA_PATH,
            collection_name=COLLECTION_NAME
        )
        for item in tqdm.tqdm(SHOP_DATA, desc="Создание базы", unit="товар"):
            chroma_db.add_texts(
                texts=[item["text"]],
                metadatas=[item["metadata"]],
                ids=[str(item["metadata"]["id"])]
            )
        logger.info(f"Chroma DB создана за {time.time() - start_time:.2f} сек")
        
        return chroma_db
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise

def connect_to_chroma():
    """Подключение к существующей базе Chroma."""
    try:
        logger.info("Загрузка модели эмбеддингов...")
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",# sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
            model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        # embeddings = OpenAIEmbeddings(
        #     model="text-embedding-3-small",
        #     api_key="sk-9rfsKOTg9ThEaqO0Cp4BMJAmFBH8DTLF",
        #     base_url=API_URL
        # )

        chroma_db = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
        )

        logger.success("Успешное подключение к базе Chroma")
        return chroma_db
    except Exception as e:
        logger.error(f"Ошибка подключения к Chroma: {e}")
        raise


def search_products(db, query: str, metadata_filter: dict = None, k: int = 4):
    """
    Поиск страниц по запросу и метаданным.

    Args:
        query (str): Текстовый запрос для поиска
        metadata_filter (dict): Опциональный фильтр по метаданным
        k (int): Количество результатов для возврата

    Returns:
        list: Список найденных документов с их метаданными
    """
    try:
        chroma_db = db
        results = chroma_db.similarity_search_with_score(
            query, k=k, filter=metadata_filter
        )

        # logger.info(f"Найдено {len(results)} результатов для запроса: {query}")
        formatted_results = []
        for doc, score in results:
            formatted_results.append(
                {
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score,
                }
            )
        return formatted_results
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        raise

def ai_list2list(db, names):
    return [search_products(db, name, k=6) for name in names]
# test

def build_chroma_db(data: list, collection_name: str = "my_collection", persist_dir: str = "./chroma_db"):
    chroma_client = chromadb.PersistentClient(
        path=persist_dir
    )
    collection = chroma_client.get_or_create_collection(name=collection_name)

    async def fetch_embedding(client: httpx.AsyncClient, text: str, id_):
        print(len(str(id_))*"\r", id_, end="")
        response = await client.post(
            API_URL,
            json={"input": text, "model": MODEL, "encoding_format": "float"},
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    async def process():
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [fetch_embedding(client, item["text"], item["metadata"]["id"]) for item in tqdm.tqdm(data)]
            embeddings = await asyncio.gather(*tasks)

            for i, (item, embedding) in tqdm.tqdm(enumerate(zip(data, embeddings))):
                collection.add(
                    ids=[f"id_{i}"],
                    documents=[item["text"]],
                    embeddings=[embedding],
                    metadatas=[item.get("metadata", {})]
                )
        chroma_client.persist()

    asyncio.run(process())


# if __name__ == "__main__":
    # db = connect_to_chroma()
    # while True:
    #     quer = input()
    #     print("Наименование\tартикул\tпроизводитель\tсходимость")
    #     for prod in search_products(db, quer):
    #         print(prod["text"]+"\t"+prod["metadata"]["article"]+"\t"+prod["metadata"]["manufactor"]+"\t"+str(prod["similarity_score"]))
    
    # asyncio.run(generate_chroma_db_async())
    # build_chroma_db(db2json(), COLLECTION_NAME, CHROMA_PATH)