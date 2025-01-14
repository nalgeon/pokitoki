"""File processor for handling document attachments."""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
import concurrent.futures

from markitdown import MarkItDown
from openai import OpenAI  # Синхронная версия
from telegram import Document, PhotoSize

from bot.config import config

logger = logging.getLogger(__name__)


class FileProcessor:
    """Processes document attachments using MarkItDown."""

    def __init__(self):
        """Initializes file processor with config settings."""
        self.max_file_size = (
            config.files.max_file_size * 1024 * 1024
        )  # Convert MB to bytes
        self.supported_extensions = config.files.supported_extensions
        # Создаем синхронный клиент
        self.sync_client = OpenAI(api_key=config.openai.api_key)
        self.md = MarkItDown(llm_client=self.sync_client, llm_model=config.openai.model)
        # Создаем пул потоков
        self.executor = concurrent.futures.ThreadPoolExecutor()

    async def process_files(
        self, documents: List[Document], photos: List[PhotoSize]
    ) -> Optional[str]:
        """Processes multiple files and returns combined content."""
        if not documents and not photos:
            return None

        tasks = []

        # Process documents
        for doc in documents:
            tasks.append(self._process_document(doc))

        # Process photos - берем только самое большое фото
        if photos:
            largest_photo = max(photos, key=lambda p: p.file_size)
            tasks.append(self._process_photo(largest_photo))

        # Wait for all files to be processed
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        processed_content = []
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                logger.error(f"Failed to process file {i}: {result}")
                continue
            if result and isinstance(result, tuple):
                filename, content = result
                processed_content.append(
                    f"<file_{filename}>{content}</file_{filename}>"
                )

        return "\n\n".join(processed_content) if processed_content else None

    async def _process_document(self, document: Document) -> Optional[Tuple[str, str]]:
        """Processes a single document."""
        try:
            if document.file_size > self.max_file_size:
                raise ValueError(
                    f"File is too large ({document.file_size/1024/1024:.1f}MB). "
                    f"Maximum size is {self.max_file_size/1024/1024:.1f}MB."
                )

            file_name = document.file_name.lower()
            file_ext = Path(file_name).suffix.lower()

            if file_ext not in self.supported_extensions:
                raise ValueError(f"Unsupported file type: {file_ext}")

            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
                file_path = Path(tmp_file.name)

            # Download file
            file = await document.get_file()
            await file.download_to_drive(file_path)

            try:
                # Process file in thread
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor, lambda: self.md.convert(str(file_path))
                )

                if not result.text_content:
                    logger.warning(f"No content extracted from {document.file_name}")
                    return None

                return document.file_name, result.text_content

            finally:
                # Cleanup
                file_path.unlink()

        except Exception as e:
            logger.error(f"Failed to process document: {e}")
            return None

    async def _process_photo(self, photo: PhotoSize) -> Optional[Tuple[str, str]]:
        """Processes a single photo."""
        try:
            logger.info(
                f"Processing photo: size={photo.file_size}, id={photo.file_unique_id}"
            )

            if photo.file_size > self.max_file_size:
                raise ValueError(
                    f"Image is too large ({photo.file_size/1024/1024:.1f}MB). "
                    f"Maximum size is {self.max_file_size/1024/1024:.1f}MB."
                )

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                file_path = Path(tmp_file.name)

            # Download file
            file = await photo.get_file()
            await file.download_to_drive(file_path)
            logger.info(f"Photo downloaded to {file_path}")

            try:
                # Process image with custom prompt in thread
                logger.info("Starting photo recognition")
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    lambda: self.md.convert(
                        str(file_path), llm_prompt=config.files.image_recognition_prompt
                    ),
                )
                logger.info("Photo recognition completed")
                return f"image_{photo.file_unique_id}", result.text_content

            finally:
                # Cleanup
                file_path.unlink()

        except Exception as e:
            logger.error(f"Failed to process photo: {e}")
            return None

    def __del__(self):
        """Cleanup executor on deletion."""
        self.executor.shutdown(wait=False)
