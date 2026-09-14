from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta import ColumnInfo, ColumnMetric, MetricInfo, TableInfo
from app.repositories import (
    DWMetadataRepository,
    ESColumnValueRepository,
    MetaRepository,
    QdrantMetadataRepository,
)

DEFAULT_META_CONFIG_PATH = Path(__file__).parents[3] / "conf" / "meta_config.yaml"


@dataclass(frozen=True)
class MetaSyncResult:
    table_count: int
    column_count: int
    metric_count: int
    column_metric_count: int
    qdrant_point_count: int
    es_document_count: int


class MetaSyncService:
    def __init__(
        self,
        meta_session: AsyncSession,
        dw_session: AsyncSession,
        config_path: Path = DEFAULT_META_CONFIG_PATH,
        dw_schema: str = "dw",
        qdrant_client: Any | None = None,
        embedding_client: Any | None = None,
        qdrant_collection_name: str | None = None,
        qdrant_embedding_size: int | None = None,
        es_client: Any | None = None,
        es_index_name: str | None = None,
    ):
        self.meta_repository = MetaRepository(meta_session)
        self.dw_repository = DWMetadataRepository(dw_session)
        self.qdrant_repository = (
            QdrantMetadataRepository(qdrant_client, embedding_client)
            if qdrant_client is not None and embedding_client is not None
            else None
        )
        self.es_repository = ESColumnValueRepository(es_client) if es_client is not None else None
        self.meta_session = meta_session
        self.config_path = config_path
        self.dw_schema = dw_schema
        self.qdrant_collection_name = qdrant_collection_name
        self.qdrant_embedding_size = qdrant_embedding_size
        self.es_index_name = es_index_name

    async def sync(self) -> MetaSyncResult:
        config = self._load_config()
        table_configs = self._get_object_list(config, "tables")
        metric_configs = self._get_object_list(config, "metrics")

        table_names = [self._require_text(table, "name", "table") for table in table_configs]
        dw_column_types = await self.dw_repository.get_column_types(self.dw_schema, table_names)
        columns_by_table = self._build_columns_by_table(table_configs)
        self._validate_dw_columns(columns_by_table, dw_column_types)
        column_examples = await self.dw_repository.get_column_examples(
            self.dw_schema,
            columns_by_table,
        )

        tables, columns, configured_column_ids = self._build_table_metadata(
            table_configs,
            dw_column_types,
            column_examples,
        )
        metrics, column_metrics = self._build_metric_metadata(
            metric_configs,
            configured_column_ids,
        )

        async with self.meta_session.begin():
            await self.meta_repository.replace_all(tables, columns, metrics, column_metrics)

        qdrant_point_count = await self._sync_qdrant(tables, columns, metrics)
        es_document_count = await self._sync_es(table_configs, columns)

        return MetaSyncResult(
            table_count=len(tables),
            column_count=len(columns),
            metric_count=len(metrics),
            column_metric_count=len(column_metrics),
            qdrant_point_count=qdrant_point_count,
            es_document_count=es_document_count,
        )

    def _load_config(self) -> dict[str, Any]:
        with self.config_path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}
        if not isinstance(config, dict):
            raise ValueError(f"元数据配置必须是 YAML 对象: {self.config_path}")
        return config

    def _build_table_metadata(
        self,
        table_configs: list[dict[str, Any]],
        dw_column_types: dict[str, dict[str, str]],
        column_examples: dict[str, dict[str, list[Any]]],
    ) -> tuple[list[TableInfo], list[ColumnInfo], set[str]]:
        tables: list[TableInfo] = []
        columns: list[ColumnInfo] = []
        configured_column_ids: set[str] = set()
        missing_columns: list[str] = []

        for table_config in table_configs:
            table_name = self._require_text(table_config, "name", "table")
            table_columns = self._get_object_list(table_config, "columns", f"table {table_name}")

            tables.append(
                TableInfo(
                    id=table_name,
                    name=table_name,
                    role=table_config.get("role"),
                    description=table_config.get("description"),
                )
            )

            for column_config in table_columns:
                column_name = self._require_text(column_config, "name", f"table {table_name} column")
                column_id = f"{table_name}.{column_name}"
                column_type = dw_column_types.get(table_name, {}).get(column_name)
                if column_type is None:
                    missing_columns.append(column_id)
                    continue

                configured_column_ids.add(column_id)
                columns.append(
                    ColumnInfo(
                        id=column_id,
                        name=column_name,
                        type=column_type,
                        role=column_config.get("role"),
                        examples=column_examples.get(table_name, {}).get(column_name, []),
                        description=column_config.get("description"),
                        alias=column_config.get("alias"),
                        table_id=table_name,
                    )
                )

        if missing_columns:
            raise ValueError("配置中的字段在 DW 中不存在: " + ", ".join(missing_columns))

        return tables, columns, configured_column_ids

    def _build_columns_by_table(
        self,
        table_configs: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        columns_by_table: dict[str, list[str]] = {}

        for table_config in table_configs:
            table_name = self._require_text(table_config, "name", "table")
            table_columns = self._get_object_list(table_config, "columns", f"table {table_name}")
            columns_by_table[table_name] = [
                self._require_text(column_config, "name", f"table {table_name} column")
                for column_config in table_columns
            ]

        return columns_by_table

    def _build_synced_columns_by_table(
        self,
        table_configs: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        columns_by_table: dict[str, list[str]] = {}

        for table_config in table_configs:
            table_name = self._require_text(table_config, "name", "table")
            table_columns = self._get_object_list(table_config, "columns", f"table {table_name}")
            synced_columns = [
                self._require_text(column_config, "name", f"table {table_name} column")
                for column_config in table_columns
                if column_config.get("sync") is True
            ]
            if synced_columns:
                columns_by_table[table_name] = synced_columns

        return columns_by_table

    @staticmethod
    def _validate_dw_columns(
        columns_by_table: dict[str, list[str]],
        dw_column_types: dict[str, dict[str, str]],
    ) -> None:
        missing_columns = [
            f"{table_name}.{column_name}"
            for table_name, column_names in columns_by_table.items()
            for column_name in column_names
            if column_name not in dw_column_types.get(table_name, {})
        ]
        if missing_columns:
            raise ValueError("配置中的字段在 DW 中不存在: " + ", ".join(missing_columns))

    def _build_metric_metadata(
        self,
        metric_configs: list[dict[str, Any]],
        configured_column_ids: set[str],
    ) -> tuple[list[MetricInfo], list[ColumnMetric]]:
        metrics: list[MetricInfo] = []
        column_metrics: list[ColumnMetric] = []
        missing_references: list[str] = []

        for metric_config in metric_configs:
            metric_name = self._require_text(metric_config, "name", "metric")
            relevant_columns = self._get_list(
                metric_config,
                "relevant_columns",
                f"metric {metric_name}",
            )

            metrics.append(
                MetricInfo(
                    id=metric_name,
                    name=metric_name,
                    description=metric_config.get("description"),
                    relevant_columns=relevant_columns,
                    alias=metric_config.get("alias"),
                )
            )

            for column_id in relevant_columns:
                if not isinstance(column_id, str) or not column_id:
                    raise ValueError(f"指标 {metric_name} 的 relevant_columns 必须是非空字符串列表")
                if column_id not in configured_column_ids:
                    missing_references.append(f"{metric_name} -> {column_id}")
                    continue
                column_metrics.append(ColumnMetric(column_id=column_id, metric_id=metric_name))

        if missing_references:
            raise ValueError("指标引用的字段不在配置中: " + ", ".join(missing_references))

        return metrics, column_metrics

    async def _sync_qdrant(
        self,
        tables: list[TableInfo],
        columns: list[ColumnInfo],
        metrics: list[MetricInfo],
    ) -> int:
        if self.qdrant_repository is None:
            return 0
        if self.qdrant_collection_name is None:
            raise ValueError("缺少 Qdrant collection_name 配置")
        if self.qdrant_embedding_size is None:
            raise ValueError("缺少 Qdrant embedding_size 配置")

        return await self.qdrant_repository.replace_metadata(
            self.qdrant_collection_name,
            self.qdrant_embedding_size,
            tables,
            columns,
            metrics,
        )

    async def _sync_es(
        self,
        table_configs: list[dict[str, Any]],
        columns: list[ColumnInfo],
    ) -> int:
        if self.es_repository is None:
            return 0
        if self.es_index_name is None:
            raise ValueError("缺少 ES index_name 配置")

        synced_columns_by_table = self._build_synced_columns_by_table(table_configs)
        column_values = await self.dw_repository.get_distinct_column_values(
            self.dw_schema,
            synced_columns_by_table,
        )
        return await self.es_repository.replace_column_values(
            self.es_index_name,
            columns,
            column_values,
        )

    @staticmethod
    def _get_list(
        config: dict[str, Any],
        key: str,
        context: str = "config",
    ) -> list[Any]:
        values = config.get(key, [])
        if not isinstance(values, list):
            raise ValueError(f"{context} 的 {key} 必须是列表")
        return values

    @classmethod
    def _get_object_list(
        cls,
        config: dict[str, Any],
        key: str,
        context: str = "config",
    ) -> list[dict[str, Any]]:
        values = cls._get_list(config, key, context)
        if not all(isinstance(value, dict) for value in values):
            raise ValueError(f"{context} 的 {key} 每一项必须是对象")
        return values

    @staticmethod
    def _require_text(config: dict[str, Any], key: str, context: str) -> str:
        value = config.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{context} 缺少必填字符串字段: {key}")
        return value
