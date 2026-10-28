import os
import time
import asyncio
import logging

logger = logging.getLogger(__name__)


async def auto_clean_downloads(folder: str = "downloads", max_age_minutes: int = 30, check_interval_minutes: int = 15):
    """
    Фоново убирает мусор из /downloads
    :param folder: Папка, которую чистим.
    :param max_age_minutes: Если файл старее за это время.
    :param check_interval_minutes: Как часто заглядывать в папку.
    """
    logger.info(f"[CLEANUP] Фоновый уборщик запущено с интервалом очистки в {check_interval_minutes} мин.")

    while True:
        try:
            if os.path.exists(folder):
                current_time = time.time()
                deleted_count = 0

                # Перебирает все файлы в папке
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)

                    # Проверка на файл/папку
                    if os.path.isfile(file_path):
                        # Получаем время последней модификации файла
                        file_mtime = os.path.getmtime(file_path)

                        # Разница во времени между "сейчас" и "временем создания файла" (в секундах)
                        age_seconds = current_time - file_mtime

                        # Если файл старее за лимит
                        if age_seconds > (max_age_minutes * 60):
                            try:
                                os.remove(file_path)
                                deleted_count += 1
                            except Exception as e:
                                logger.error(f"❌ [CLEANUP] Не смог удалить {filename}: {e}")

                if deleted_count > 0:
                    logger.info(f"♻️ [CLEANUP] Успешно удалено {deleted_count} старых файлов из папки '{folder}'.")

        except Exception as e:
            logger.error(f"❌ [CLEANUP] Критическая ошибка в цикле очистки: {e}")

        # Спим до следующей проверки
        await asyncio.sleep(check_interval_minutes * 60)