# Index Store
import config

if config.MindSpark_ENV == "production":
    from llama_index.storage.index_store.redis import RedisIndexStore

    INDEX_STORE = RedisIndexStore.from_host_and_port(
        host=config.REDIS_HOST, port=config.REDIS_PORT, namespace="think"
    )
elif config.MindSpark_ENV == "development":
    from llama_index.core.storage.index_store import SimpleIndexStore

    INDEX_STORE = SimpleIndexStore()
