from __future__ import annotations
import io
import logging
from io import BytesIO
from typing import TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from types import TracebackType
    from boto3_type_annotations.s3 import Client

logger = logging.getLogger(__name__)


class FileManager:
    def __init__(self, client: Client, default_bucket: str):
        self.client = client
        self.default_bucket = default_bucket

    class Downloader:
        def __init__(self, client: Client, bucket: str, key: str):
            self.client = client
            self.bucket = bucket
            self.key = key

        def __enter__(self):
            if (self.bucket is None):
                msg = "Source bucket not provided"
                raise AttributeError(msg)

            bio = BytesIO()
            logger.debug("Download: %s", self.key)
            self.client.download_fileobj(self.bucket, self.key, bio)
            return bio.getvalue()

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ):
            logger.debug("exit")

    def _file_download(self, bucket: str, key: str) -> BytesIO:
        return FileManager.Downloader(self.client, bucket or self.default_bucket, key)

    def load_parquet_to_df(self, bucket: str, key: str) -> pd.DataFrame:
        with self._file_download(bucket, key) as content:
            logging.debug("load_parquet_to_df: %s", key)
            return pd.read_parquet(io.BytesIO(content), engine="pyarrow")

    def save_tables(self, tables: list[tuple[str, pd.DataFrame]]) -> None:
        for path, data in tables:
            self.save_df_to_parquet(path=path, df=data)

    def save_df_to_parquet(self, df: pd.DataFrame, path: str) -> None:
        pq_buffer = io.BytesIO()
        df.to_parquet(pq_buffer, engine="pyarrow", compression="gzip", index=False)
        self.client.put_object(
            Body=(pq_buffer.getvalue()),
            Bucket=self.default_bucket,
            Key=path,
        )

