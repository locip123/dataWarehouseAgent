import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.conf.app_config import app_config
from app.core.log import logger
from app.services import MetaSyncService


async def main() -> None:
    try:
        meta_mysql_client_manager.init()
        dw_mysql_client_manager.init()
        qdrant_client_manager.init()
        es_client_manager.init()
        embedding_client_manager.init()

        async with AsyncSession(
            meta_mysql_client_manager.engine,
            autoflush=True,
            expire_on_commit=False,
        ) as meta_session:
            async with AsyncSession(
                dw_mysql_client_manager.engine,
                autoflush=True,
                expire_on_commit=False,
            ) as dw_session:
                result = await MetaSyncService(
                    meta_session,
                    dw_session,
                    qdrant_client=qdrant_client_manager.client,
                    embedding_client=embedding_client_manager.client,
                    qdrant_collection_name=app_config.qdrant.collection_name,
                    qdrant_embedding_size=app_config.qdrant.embedding_size,
                    es_client=es_client_manager.client,
                    es_index_name=app_config.es.index_name,
                ).sync()

        logger.info(
            (
                "元数据同步完成: tables={}, columns={}, metrics={}, "
                "column_metrics={}, qdrant_points={}, es_documents={}"
            ),
            result.table_count,
            result.column_count,
            result.metric_count,
            result.column_metric_count,
            result.qdrant_point_count,
            result.es_document_count,
        )
    except Exception:
        logger.exception("元数据同步失败")
        raise
    finally:
        if embedding_client_manager.client is not None:
            await embedding_client_manager.close()
        if es_client_manager.client is not None:
            await es_client_manager.close()
        if qdrant_client_manager.client is not None:
            await qdrant_client_manager.close()
        if meta_mysql_client_manager.engine is not None:
            await meta_mysql_client_manager.close()
        if dw_mysql_client_manager.engine is not None:
            await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
