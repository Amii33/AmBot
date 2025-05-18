from aiogram.types import InputFile
from io import BytesIO
import logging

async def send_clean_media(
    bot,
    user_id: int,
    file_id: str,
    media_type: str = "photo",  # "photo" или "video"
    caption: str = "",
    **kwargs
):
    """
    Отправляет фото или видео без отображения file_id.
    
    :param bot: Экземпляр бота
    :param user_id: ID пользователя
    :param file_id: file_id медиа из Telegram
    :param media_type: Тип медиа ("photo" или "video")
    :param caption: Подпись (опционально)
    :param kwargs: Доп. параметры для send_photo/send_video
    """
    try:
        # 1. Получаем информацию о файле
        file = await bot.get_file(file_id)
        logging.info(f"Downloading {media_type} file: {file.file_path}")
        
        # 2. Скачиваем в оперативную память
        downloaded = await bot.download_file(file.file_path)
        media_data = downloaded.read()
        
        # 3. Создаем чистый файловый объект
        media_buffer = BytesIO(media_data)
        media_buffer.name = f"{media_type}.{'jpg' if media_type == 'photo' else 'mp4'}"
        
        # 4. Отправляем медиа
        logging.info(f"Sending {media_type} to user {user_id}")
        await bot.send_chat_action(user_id, f'upload_{media_type}')
        
        send_method = getattr(bot, f"send_{media_type}")
        await send_method(
            chat_id=user_id,
            **{media_type: InputFile(media_buffer)},
            caption=caption or " ",  # Невидимый пробел, если caption пуст
            parse_mode=None,
            disable_notification=True,
            **kwargs
        )
        
        # 5. Закрываем буфер
        media_buffer.close()
        logging.info(f"{media_type.capitalize()} sent successfully")
        
    except Exception as e:
        logging.error(f"Error sending {media_type}: {str(e)}", exc_info=True)
        
        # Fallback: пытаемся отправить оригинальным способом
        try:
            send_method = getattr(bot, f"send_{media_type}")
            await send_method(
                chat_id=user_id,
                **{media_type: file_id},
                caption=caption or " ",
                parse_mode=None,
                **kwargs
            )
        except Exception as fallback_error:
            logging.error(f"{media_type.capitalize()} fallback failed: {str(fallback_error)}")
            raise

# Старые функции для обратной совместимости
async def send_clean_photo(bot, user_id: int, file_id: str, caption: str = ""):
    """Отправляет фото (обёртка над send_clean_media)."""
    return await send_clean_media(
        bot, user_id, file_id, media_type="photo", caption=caption
    )

async def send_clean_video(bot, user_id: int, file_id: str):
    """Отправляет видео (обёртка над send_clean_media)."""
    return await send_clean_media(
        bot, user_id, file_id, media_type="video", supports_streaming=True
    )