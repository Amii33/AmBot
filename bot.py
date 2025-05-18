import logging
import re
import asyncio
import requests
import pickle
import time  
import glob
import os
import shutil
print(os.access(".", os.W_OK))
from typing import Dict, Any
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.enums import ParseMode
from aiogram.utils.media_group import MediaGroupBuilder
from video_photo_utils import send_clean_video, send_clean_photo
from io import BytesIO
from aiogram.types import ReplyKeyboardRemove

class PickleDatabase:
    def __init__(self, filename: str):
        self.filename = filename
        self._ensure_directory_exists()
        self.data = self._safe_load()
        
    def _ensure_directory_exists(self):
        """Создает директорию, если она не существует"""
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        
    def _safe_load(self) -> Dict[int, Any]:
        """Безопасная загрузка данных с защитой от поврежденных файлов"""
        if not os.path.exists(self.filename):
            return {}
            
        try:
            with open(self.filename, 'rb') as f:
                # Проверяем, что файл не пустой
                if os.path.getsize(self.filename) > 0:
                    return pickle.load(f)
                return {}
        except (EOFError, pickle.UnpicklingError) as e:
            print(f"Ошибка загрузки БД: {e}. Создаю новую БД.")
            return {}
            
    def _safe_save(self):
        """Безопасное сохранение с созданием резервной копии"""
        try:
            # Сначала сохраняем во временный файл
            temp_filename = self.filename + '.tmp'
            with open(temp_filename, 'wb') as f:
                pickle.dump(self.data, f)
                
            # Затем заменяем основной файл
            if os.path.exists(self.filename):
                os.replace(self.filename, self.filename + '.bak')
            os.rename(temp_filename, self.filename)
            
        except Exception as e:
            print(f"Ошибка сохранения БД: {e}")
            raise
            
    def update_user(self, user_id: int, user_data: Dict[str, Any]):
        """Обновление данных пользователя"""
        self.data[user_id] = user_data
        self._safe_save()

doc_url3 = "https://rutracker.org/forum/tracker.php?nm=capture"
doc_url4 = "https://www.utorrent.com"
doc_url5 = "https://appstorrent.ru"
doc_url6 = "https://transmissionbt.com"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Конфигурация бота
API_TOKEN = '7283157723:AAE0B9T6V4pNQ7TxyKF-1q9CxwPwrsltoT8'
ADMIN_ID = 167162909  # ID администратора

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot)

# Состояния бота
class Form(StatesGroup):
    language = State()        # Выбор языка
    user_data = State()       # Ввод телефона
    agree = State()           # Согласие с политикой
    post_content = State()    # Создание поста: текст
    post_media = State()      # Создание поста: медиа
    post_confirm = State()    # Подтверждение поста
    post_language = State()

# Вспомогательные функции
web_app_url = "https://script.google.com/macros/s/AKfycbwZvyf6UHxf8R-7ZNbl0tarBXyvyBdwumzfp_xTTlJ5IpG86tgddXbX4NvwFUWeNgQ7VQ/exec"
async def save_to_google_sheets(user_data: dict):
    try:
        response = requests.post(
            web_app_url,
            json=user_data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            print("Данные отправлены!")
    except Exception as e:
        print(f"Ошибка: {e}")

async def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id == ADMIN_ID

def get_user_lang(user_id: int) -> str:
    """Возвращает язык пользователя"""
    return db.data.get(user_id, {}).get('language', 'ru')

def create_admin_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Создает клавиатуру для админ-панели"""
    builder = ReplyKeyboardBuilder()
    if lang == 'ru':
        builder.row(KeyboardButton(text="📝 Создать пост"))
        builder.row(KeyboardButton(text="❌ Отмена"))
    else:
        builder.row(KeyboardButton(text="📝 Create post"))
        builder.row(KeyboardButton(text="❌ Cancel"))
    return builder.as_markup(resize_keyboard=True)

async def show_admin_panel(user_id: int, lang: str):
    """Показывает админ-панель"""
    await bot.send_message(
        chat_id=user_id,
        text="👑 Админ-панель" if lang == 'ru' else "👑 Admin panel",
        reply_markup=create_admin_keyboard(lang)
    )

async def send_course_offer(user_id: int, lang: str):
    """Отправляет предложение о курсе через 1 час"""
    await asyncio.sleep(60)  # Ждем 1 час
    
    try:

        if lang == 'ru':
            caption = """💋 Если тебе понравился урок и хочется прокачаться ещё круче, приглашаю тебя на мой авторский курс <b>American PRO.</b>\n
Там я собрала все самые рабочие техники, которыми сама пользуюсь каждый день, чтобы получать тот самый дорогой цвет, чистую ретушь и стильные кадры, которые хочется рассматривать бесконечно.\n
<b>American PRO</b> — <i>это про уверенность в своих работах, про результат, который видно сразу, и про навыки, которые действительно меняют уровень!\n
Если чувствуешь, что тебе откликается - буду рада видеть тебя! Обещаю: будет интересно, понятно и вдохновляюще!</i> ❤️\n
Оплатить <b>American PRO</b> можно максимально удобно: рассрочки, оплата долями, сплит — всё для того, чтобы твой рост начался уже сейчас, а не когда-нибудь потом.\n
Приобрести можно здесь: https://antoinettass.ru/AmericanPro\n
Хочешь обратную связь — пиши мне прямо сюда @antoinettass  ❤️"""
            photo_ids = [
                "AgACAgIAAxkBAAIIEGglWxDibybePkl9NDogGJTwc2u9AAIN6jEbqbIxSbqG6rf5OEaAAQADAgADeQADNgQ", 
                "AgACAgIAAxkBAAIIEmglWzJN2xQfa2NzjbiR_iWIA2EiAAIO6jEbqbIxSeTAzOZNy6GjAQADAgADeQADNgQ",
                "AgACAgIAAxkBAAIIFGglW0tGcYE-JU-pIJtYikqZPtOUAAIP6jEbqbIxSbO7QlLl_EWfAQADAgADeQADNgQ"
            ]
        else:
            caption = """If you enjoyed the lesson and want to level up even more, i invite you to my author's course <b>American PRO.</b>\n
There I collected all the most working techniques that i use everyday to get the most expensive color, clean retouching and stylish shots that I want to look at endlessly.\n\n<b>American PRO</b><i> is about confidence in your work, about results that are immediately visible, and about skills that really change the level!\nIf you feel like you're responding, I'll be glad to see you! I promise: it will be interesting, understandable and inspiring!</i>\n\nYou can pay for <b>American PRO</b> via Visa or MasterCard, as well as a crypto wallet.\n\nTo purchase the course, write to me in @antoinettass telegram or on instagram using the same nickname. ❤️"""
            photo_ids = [
                "AgACAgIAAxkBAAIIEGglWxDibybePkl9NDogGJTwc2u9AAIN6jEbqbIxSbqG6rf5OEaAAQADAgADeQADNgQ",
                "AgACAgIAAxkBAAIIEmglWzJN2xQfa2NzjbiR_iWIA2EiAAIO6jEbqbIxSeTAzOZNy6GjAQADAgADeQADNgQ",
                "AgACAgIAAxkBAAIIFGglW0tGcYE-JU-pIJtYikqZPtOUAAIP6jEbqbIxSbO7QlLl_EWfAQADAgADeQADNgQ"
            ]

        # Создаем группу медиа
        media = MediaGroupBuilder()
        
        # Добавляем первую фотографию с подписью
        media.add_photo(
            media=photo_ids[0],
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        
        # Добавляем остальные фотографии без подписи
        for photo_id in photo_ids[1:]:
            media.add_photo(media=photo_id)
        
        # Отправляем медиагруппу
        await bot.send_media_group(
            chat_id=user_id,
            media=media.build()
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки предложения курса пользователю {user_id}: {e}")
        # Попробуем отправить текст отдельным сообщением, если медиагруппа не отправилась
        try:
            await bot.send_message(
                chat_id=user_id,
                text=caption,
                parse_mode=ParseMode.HTML
            )
        except Exception as fallback_error:
            logger.error(f"❌ Ошибка отправки fallback-сообщения пользователю {user_id}: {fallback_error}")


async def send_followup_message(user_id: int, lang: str):
    """Отправляет follow-up сообщение через 1 день"""
    try:
        if lang == 'ru':
            # Русская версия - 1 картинка и кликабельная ссылка
            await bot.send_photo(
                chat_id=user_id,
                photo="AgACAgIAAxkBAAIIHmglXGCMAAHOZynJQacIsCVwzpt8eAACK-sxG5v3KUln9NDEBaWVZAEAAwIAA3kAAzYE",  # Замените на реальный file_id картинки
                caption="""Привет, это Антуанетта ❤️\n
Как тебе материалы? Уже появляются идеи, как применить?🧚‍♀
Если хочется большего — вот ссылка на мой полноценный курс:""",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔴🔴🔴 СМОТРЕТЬ ПРОГРАММУ 🔴🔴🔴",
                        url="https://antoinettass.ru/AmericanPro"
                    )]
                ])
            )
                
        else:
            # Английская версия - 3 картинки без ссылки
            media = MediaGroupBuilder(
                caption="""Hey, it's Antoinetta! ❤️\n
How did you like the materials? Got any ideas already on how to use them?🧚‍♀ \n
If you're ready to go further — here's a sneak peek at what's included in the course"""
            )
            photo_ids = ["AgACAgIAAxkBAAIIFmglXA75cqx0EcPt4PxcampUoYsQAAIQ6jEbqbIxSQcOMFWLWemLAQADAgADeQADNgQ", "AgACAgIAAxkBAAIIGGglXBdwAhNgneWCqORJ5rDsmSMUAAIR6jEbqbIxSQaJvVuyicD9AQADAgADeQADNgQ", "AgACAgIAAxkBAAIIGmglXCaEIN6h-LxYj7CBKLA3KOmpAAIS6jEbqbIxSX8J-Dt4nLD8AQADAgADeQADNgQ", "AgACAgIAAxkBAAIIHGglXDGUfdrASTu14gJvnefsfqPfAAIT6jEbqbIxSWtGtibLFWjQAQADAgADeQADNgQ"]  # Замените на реальные file_id
            for photo_id in photo_ids:
                media.add_photo(media=photo_id)
            
            await bot.send_media_group(chat_id=user_id, media=media.build())
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки follow-up сообщения пользователю {user_id}: {e}")

async def schedule_followup(user_id: int, lang: str):
    """Планирует отправку follow-up сообщения через 1 день"""
    await asyncio.sleep(120)  # Ждем 1 день (86400 секунд)
    await send_followup_message(user_id, lang)

# База данных пользователей
db_path = "/home/ra59622/telegram_bot/data/bot_database.pkl" # Уточните правильный путь
db = PickleDatabase(db_path)
if not db.data:
    db.data = {}
    db._safe_save()

# Основной поток
@dp.message(Command("start"))
async def send_welcome(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.set_state(Form.language)
    
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🇷🇺 Русский'), KeyboardButton(text='🇬🇧 English')]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "Приветик! 💋👋🏻 \nВыбери язык, на котором тебе будет удобнее получать материалы:\n\n"
        "Hey there! 💋👋🏻 \nChoose the language you'd prefer to receive the materials in:",
        reply_markup=markup
    )

@dp.message(Form.language)
async def process_language(message: Message, state: FSMContext):
    """Обработка выбора языка"""
    lang = 'ru' if message.text == '🇷🇺 Русский' else 'en'
    await state.update_data(language=lang)
    db.update_user(message.from_user.id, {'language': lang})
    
    if lang == 'ru':
        text = """💌Напиши, пожалуйста, одним сообщением:\n\nТвоё имя, почту и номер телефона\n(вот так, через запятую⤵️)\n\n*Пример:*\nАнна, mail@mail.ru, +79998887766"""
    else:
        text = """💌Please, write in one message:\n\nYour name, email and phone number\n(like this, separated by commas⤵️)\n\n*Example:*\nAnna, mail@mail.com, +79998887766"""

    await state.set_state(Form.user_data)
    await message.answer(
        text, 
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove()  # Убираем клавиатуру после выбора
    )


@dp.message(Form.user_data)
async def process_user_data(message: Message, state: FSMContext):
    """Обработка введенных данных (имя, email, телефон)"""
    lang = (await state.get_data()).get('language', 'ru')
    user_input = message.text
    
    # Парсим ввод (ожидаем формат: "Имя, email, телефон")
    try:
        name, email, phone = [part.strip() for part in user_input.split(',')]
    except ValueError:
        error_text = ("⚠️ Неверный формат. Введите: Имя, email, телефон\n"
                     "<b>Пример:</b> Анна, mail@mail.ru, +79998887766"
                     if lang == 'ru'
                     else "⚠️ Invalid format. Use: Name, email, phone\n"
                     "<b>Example:</b> John, john@gmail.com, +79998887766")
        await message.answer(error_text, parse_mode=ParseMode.HTML)
        return

    # Валидация email
    if not email or not re.fullmatch(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', email):
        error_text = ("📩 Хм, кажется, почта указана не совсем корректно.\nПроверь, пожалуйста, чтобы был и @, и домен\n(например, .com, .ru, .me и т.п.)\n\n"
                     "<b>Пример:</b>\nanna@mail.ru ✅\nanna@justtext ❌\n\nЕсли не уверен(а) — просто скопируй адрес из почты, так надёжнее 🙏🏻"
                     if lang == 'ru'
                     else "📩 Hmm, it seems the email is not quite correct.\nPlease check that there is both @ and a domain\n(for example, .com, .ru, .me, etc.)\n\n"
                     "<b>Example:</b>\nanna@mail.ru ✅\nanna@justtext ❌\n\nIf you are not sure, just copy the address from the mail, it is more reliable 🙏🏻")
        await message.answer(error_text, parse_mode=ParseMode.HTML)
        return

    # Валидация телефона
    phone_digits = phone.lstrip('+')  # Удаляем + в начале для проверки количества цифр
    if not phone_digits or not phone_digits.isdigit() or not 10 <= len(phone_digits) <= 15:
        error_text = ("⚠️ Напиши, пожалуйста, номер телефона — с кодом страны.\n Можно с «+» или без - как тебе удобно. Главное — чтобы всё было\nбез ошибок.\n\n"
                     "<b>Пример:</b>\n+79998887766 или 79998887766\n(если ты из другой страны — просто укажи свой номер в привычном\nформате)"
                     if lang == 'ru'
                     else "⚠️ Please write your phone number - with the country code.\n You can with or without "+" - as you prefer. The main thing is that everything\n is without errors.\n\n"
                     "<b>Example:</b>\n+79998887766 or 79998887766\n(if you are from another country - just enter your number in the usual\nformat)")
        await message.answer(error_text, parse_mode=ParseMode.HTML)
        return

    # Если все данные валидны
    await state.update_data(name=name, email=email, phone=phone)
    await state.set_state(Form.agree)

        
    # Запрашиваем согласие с политикой
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Согласен(-на)" if lang == 'ru' else "✅ I agree",
            callback_data="agree"
        )]
    ])
    
    doc_url1 = "https://drive.google.com/file/d/1vmfhP6iUApYywHKk1qZcVWiOKuv2oA5v/view?usp=sharing"
    doc_url2 = "https://drive.google.com/file/d/1cR1AT2e9quW1XAD9aixZ092YtjGrLWy6/view?usp=sharing"
    text = (f"📄 Пожалуйста, ознакомьcя с [политикой конфиденциальности]({doc_url1}) и подтверди согласие\n\n⚠️ Чтобы материалы не продублировались — нажми на кнопку один раз и немного подожди 🙌🏻"
            if lang == 'ru'
            else f"📄 Please review the [privacy policy]({doc_url2}) and confirm your agreement\n\n⚠️ Materials are not duplicated - click the button once and wait a little 🙌🏻")
    
    await state.set_state(Form.agree)
    await message.answer(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(Form.agree, lambda c: c.data == 'agree')
async def process_agreement(callback_query: CallbackQuery, state: FSMContext):
    """Отправка уроков и планирование follow-up сообщений"""
    await callback_query.answer()
    data = await state.get_data()
    lang = data['language']
    user_id = callback_query.from_user.id

    # Получаем данные из состояния
    name = data.get("name", "")
    email = data.get("email", "")
    phone = data.get("phone", "")

    # Сохраняем данные в Google Sheets
    user_data = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "phone": phone,
        "language": lang
    }
    await save_to_google_sheets(user_data)



    
    # Приветственное сообщение с жирным текстом
    welcome_msg = {
        'ru': "<b>ГОТОВО!</b> 💋\n\nЛови бесплатные материалы — это первые шаги в нашем курсе!",
        'en': "<b>DONE!</b> 💋\n\nCatch the free materials - these are the first steps in our course!"
    }
    await callback_query.message.answer(
        welcome_msg[lang],
        parse_mode=ParseMode.HTML  # Указываем парсинг HTML-разметки
    )
    await asyncio.sleep(0.5)

    # Список уроков с медиа-материалами
    lessons = [
        # Урок 1 - 1 видео
        {
            'ru': {
                'text': """📹 1 урок. Вводный урок.\n
✨<i>Обязательно посмотри этот урок перед началом обучения!</i>""",
                'parse_mode': ParseMode.HTML,
                'media': [
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIFJ2glGalCUJPHmjujifrWmd6I3pi8AAIodgACqbIpSZUBjZfNukWINgQ"}
                ]
            },
            'en': {
                'text': """📹 1 lesson. Introductory lesson.\n
✨<i>Be sure to watch this tutorial before you start learning!\n\nThe video was dubbed using a neural program. Please don't be too critical.</i>\n\n<b>If you didn't understand something - just let me know, i`ll help!\n\nYou can always text me directly in Telegram: @antoinettass🖤</b>""",
                'parse_mode': ParseMode.HTML,
                'media': [
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIGq2glL87uRuCe8ZXIJiZoK_-NSmELAAJ1dgACqbIpSdwm4BTfFOx1NgQ"}
                ]
            }
        },
        # Урок 2 - 2 видео и 1 фото
        {
            'ru': {
                'text': """📹 2 урок. Знакомство с Photoshop. Настройка рабочей среды, цветовой профиль, горячие клавиши.\n
✨<i>В этом видео мы познакомимся с фотошопом. Настроим рабочую среду и цветовой профиль.</i>""",
                'parse_mode': ParseMode.HTML,
                'media': [
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIFNWglGl_jBKz_3TYZ76my0-eiBvZXAAI3dgACqbIpSbiCDHiYU768NgQ"},
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIFN2glG69tNox5DMrFUHo7jgAB5LbTzwACQXYAAqmyKUm6WTbmiJRrRjYE"},
                    {'type': 'photo', 'id': "AgACAgIAAxkBAAIFRWglHWxVpg3kFFyIq_teoW8-xQJ8AALT8jEbpLIpSakqW7YVXCemAQADAgADeQADNgQ"}
                    ]
            },
            'en': {
                'text': """📹 Lesson 2. Introduction to Photoshop. Setting up the work environment, color profile, keyboard shortcuts.\n
✨<i>In this video, we will get acquainted with photoshop. Let's set up the work environment and the color profile.\n\nThe video was dubbed using a neural program. Please don't be too critical. If you didn't understand something, let me know or write to me about it. I hope for your understanding!\n
📋 + I have attached the checklist "list of hotkeys</i>" """,
                'parse_mode': ParseMode.HTML,
                'media': [
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIGrWglMK29J9qzcgo2PuEaxTwnOKPTAAJ2dgACqbIpSdXQ-k9xrIdUNgQ"},
                    {'type': 'photo', 'id': "AgACAgIAAxkBAAIHBmglOUYFQvt57cAVV3jjZ2OF2vm9AAL-6jEbm_cpSaNOribt8PKTAQADAgADeQADNgQ"}
                ]
            }
        },
        # Урок 3 - 3 видео и 4 ссылки
        {
            'ru': {
                'text': f"""📹 3 урок. Проявка фотографии в Camera Raw, Lightroom, Capture One\n
✨<i>В этом видео я покажу вам начальный этап обработки фотографий в различных программах. Вы узнаете, как работать с фотографиями в каждой из них и сможете сравнить их преимущества и недостатки.</i>\n\n 👉🏻 скачать <a href="{doc_url3}">программы для Windows</a>: капчер, лайтрум, фотошоп (нужно зарегистрироваться) и перед скачиванием <a href="{doc_url4}">скачать torrent</a>\n
👉🏻 скачать <a href="{doc_url5}">программы для Mac</a>: капчер, лайтрум, фотошоп, но я не пробовала. Перед скачиванием <a href="{doc_url6}">скачать transmission</a>""",
                'parse_mode': ParseMode.HTML,
                'media': [
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIFOWglHFXWyBuEDzmItV6-u4UKII3YAAJEdgACqbIpSfIOhGTxyRObNgQ"},
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIFO2glHJEJsDe0QSwH37uluJ7XLQUsAAJGdgACqbIpSeO1_0QzXdvVNgQ"},
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIFPWglHQRgjkdw6jlo6P19RUyoT6YSAAJHdgACqbIpSYboa86u2jfmNgQ"}
                    
                ]
            },
            'en': {
                'text': f"""📹 Lesson 3. Developing photos in Camera Raw, Lightroom, Capture One.\n
✨<i>In this video, I will show you the initial stage of photo processing in various programs. You will learn how to work with photos in each of them and will be able to compare their advantages and disadvantages.</i>\n\nThe video was translated and dubbed using the Ai Magics service. Please don't be too critical. If you didn't understand something, let me know or write to me about it. I hope for your understanding!\n\n👉🏻 free download <a href="{doc_url3}">programs for Windows</a>: Capture, Lightroom, Photoshop (you need to register) and <a href="{doc_url4}"> download torrent</a> before downloading\n
👉🏻 free download <a href="{doc_url5}">programs for Mac</a>: Capture, Lightroom, Photoshop, but I haven't tried it:<a href="{doc_url6}"> download transmission</a> before downloading""",
                'parse_mode': ParseMode.HTML,
                'media': [
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIGr2glMPsOoG3SoYxlRA8vDK6OVwNZAAJ3dgACqbIpSRQIHrM8EhLVNgQ"},
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIGsWglMRyLI_XP-Jn6PYDSlzb1i6EIAAJ4dgACqbIpSR1qVWl2hw8zNgQ"},
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIGs2glMUyIyZRbqc76yYmrFU29lIDSAAJ5dgACqbIpSQNVt1WOq5hTNgQ"}
                    
                ]
            }
        },
        # Урок 4 - 3 видео
        {
            'ru': {
                'text': """📹 4 урок. Отбор фотографий в Camera Raw, Lightroom, Capture One.\n
✨<i>В этом уроке вы освоите методы быстрого и эффективного отбора фотографий из большого объема.</i>""",
                'parse_mode': ParseMode.HTML,
                'media': [
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIFP2glHSaqExCJWQ39eK6sy3769KoCAAJIdgACqbIpSbShRcQMiDToNgQ"},
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIFQWglHUAdxpVv89j8iht1ihKTYIPCAAJJdgACqbIpSd3vFFnPvEhqNgQ"},
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIFQ2glHV6kNLznDre_9evW2sF64tPkAAJKdgACqbIpSRu0x7R1A53qNgQ"}
                ]
            },
            'en': {
                'text': """📹 Lesson 4. Selecting photos in Camera Raw, Lightroom, Capture One.\n
✨<i>In this lesson, you will learn how to quickly and efficiently select photos from a large volume.\n\nThe video was translated and dubbed using the Ai Magics service. Please don't be too critical. If you didn't understand something, let me know or write to me about it. I hope for your understanding!</i>""",
                'parse_mode': ParseMode.HTML,
                'media': [
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIGtWglMW3DQAKmA1oyiC7xsvOn-__UAALcYQAClLkxSbJpYzgkAnlcNgQ"},
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIGt2glMaGzJm_lWotJhWy5LaFw7sIGAALdYQAClLkxScFL9bwtP5hsNgQ"},
                    {'type': 'video', 'id': "BAACAgIAAxkBAAIGuWglMbXU3y7-M4ZKqQ0Z7CxQkZDRAAJ6dgACqbIpSTdVumjpWyt5NgQ"}
                ]
            }
        },
        # Урок 5 - 1 видео
        {
    'ru': {
        'text': """📹 5 урок. Доп. урок. Цвет по референсу.\n
✨<i>Ура! Ты уже прошёл целый модуль - и теперь давай разберём самое интересное: </i><b>цвет</b>🎨\n\n"""
                """<i>В этом уроке мы научимся настраивать цвет, как на референсе — передавать вайб, оттенки, настроение и доводить всё до красивого финального тона.</i>\n\n"""
                """<i>ЛЕТС ГОУУУ!</i> 💥""",
        'parse_mode': ParseMode.HTML,
        'media': [
            {'type': 'video', 'id': "BAACAgIAAxkBAAIFRmglH8VjN_YP9zEHeXXAyTasiImbAAJQdgACqbIpSdVpmXL9x677NgQ"}
        ]
    },
    'en': {
        'text': """📹 Lesson 5. Additional lesson. Color by reference.\n
✨<i>Hooray! You've already completed a whole module - and now let's get to the most interesting part: </i><b>color</b>🎨\n\n"""
                """<i>In this lesson, we'll learn how to adjust the color as in the reference - to convey the vibe, shades, mood and bring everything to a beautiful final tone.</i>\n\n"""
                """<i>LETS GO!</i> 💥""",
        'parse_mode': ParseMode.HTML,
        'media': [
            {'type': 'video', 'id': "BAACAgIAAxkBAAIJKmglw5C7Sn5lE1IJMmVknWRLlJDFAAIdcgACLDExSc_KRfqkyEe3NgQ"}
        ]
    }
}
    ]

  # Отправка каждого урока
    for lesson_num, lesson in enumerate(lessons, start=1):
        lesson_data = lesson[lang]
        
        # 1. Отправляем текст урока
        await callback_query.message.answer(
            text=lesson_data['text'],
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True  # Отключаем предпросмотр ссылок
        )

        
        # 2. Отправляем медиа-материалы
        for media in lesson_data['media']:
            if media['type'] == 'video':
                await send_clean_video(
                    bot=bot,
                    user_id=callback_query.from_user.id,
                    file_id=media['id']
                )
            
            elif media['type'] == 'photo':
                await send_clean_photo(
                    bot=bot,
                    user_id=callback_query.from_user.id,
                    file_id=media['id'],
                    caption=f"Список горячих клавиш 🎲👆🏻" if lang == 'ru' else f"List of hotkeys 🎲👆🏻",
)

                            
            elif media['type'] == 'link':
                await callback_query.message.answer(
                    f"🔗 {media['text']}: {media['url']}",
                    disable_web_page_preview=True
                )
        
        # Пауза между уроками
        await asyncio.sleep(1)

    # Сохранение данных пользователя
        user_data = {
            'language': lang,
            'phone': data['phone'],
            'agreed': True,
            'reg_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             'lessons_sent': True
        }
        db.update_user(user_id, user_data)  
                          
    
    # Планирование сообщений
    asyncio.create_task(send_course_offer(user_id, lang))  # Через 1 час
    asyncio.create_task(schedule_followup(user_id, lang))  # Через 1 день
    
    # Показываем админ-панель для администратора
    if await is_admin(user_id):
        await show_admin_panel(user_id, lang)
    
    await state.clear()
    

# Админ-панель (только создание постов)
@dp.message(lambda message: message.text in ["📝 Создать пост", "📝 Create post"])
async def start_post_creation(message: Message, state: FSMContext):
    """Начало создания поста"""
    if not await is_admin(message.from_user.id):
        return
    
    lang = get_user_lang(message.from_user.id)
    
    # Предлагаем выбрать язык поста
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🇷🇺 Русский'), KeyboardButton(text='🇬🇧 English')],
            [KeyboardButton(text='❌ Отмена' if lang == 'ru' else '❌ Cancel')]
        ],
        resize_keyboard=True
    )
    
    await state.set_state(Form.post_language)
    await message.answer(
        "🌍 Выберите язык поста:" if lang == 'ru' else "🌍 Select post language:",
        reply_markup=markup
    )

@dp.message(Form.post_language)
async def process_post_language(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    post_lang = 'ru' if message.text == '🇷🇺 Русский' else 'en'
    
    await state.update_data(post_language=post_lang)
    await state.set_state(Form.post_content)
    
    await message.answer(
        "✏️ Введите текст поста на выбранном языке:" if lang == 'ru' 
        else "✏️ Enter post text in selected language:",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Form.post_content)
async def process_post_content(message: Message, state: FSMContext):
    """Обработка текста поста"""
    if not message.text:
        lang = get_user_lang(message.from_user.id)
        await message.answer(
            "⚠️ Пожалуйста, введите текст поста" if lang == 'ru' 
            else "⚠️ Please enter post text"
        )
        return
    
    await state.update_data(post_text=message.text, post_media=[])
    lang = get_user_lang(message.from_user.id)
    
    builder = ReplyKeyboardBuilder()
    if lang == 'ru':
        builder.add(KeyboardButton(text="⏭ Пропустить"), KeyboardButton(text="❌ Отмена"))
    else:
        builder.add(KeyboardButton(text="⏭ Skip"), KeyboardButton(text="❌ Cancel"))
    builder.adjust(1)
    
    await state.set_state(Form.post_media)
    await message.answer(
        "🖼 Отправьте медиа (фото, видео, документ) или нажмите 'Пропустить'" if lang == 'ru'
        else "🖼 Send media (photo, video, document) or press 'Skip'",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@dp.message(Form.post_media, lambda message: message.content_type in ['photo', 'video', 'document'])
async def process_media(message: Message, state: FSMContext):
    """Обработка медиа для поста"""
    data = await state.get_data()
    post_media = data.get('post_media', [])
    
    if message.content_type == 'photo':
        post_media.append(('photo', message.photo[-1].file_id))
    elif message.content_type == 'video':
        post_media.append(('video', message.video.file_id))
    elif message.content_type == 'document':
        post_media.append(('document', message.document.file_id))
    
    await state.update_data(post_media=post_media)
    lang = get_user_lang(message.from_user.id)
    
    await message.answer(
        "✅ Медиа добавлено. Отправьте еще или нажмите 'Готово'" if lang == 'ru'
        else "✅ Media added. Send more or press 'Done'"
    )

@dp.message(Form.post_media, lambda message: message.text in ["✅ Готово", "✅ Done", "⏭ Пропустить", "⏭ Skip"])
async def finish_media(message: Message, state: FSMContext):
    """Завершение добавления медиа"""
    lang = get_user_lang(message.from_user.id)
    data = await state.get_data()
    post_text = data.get('post_text', '')
    post_media = data.get('post_media', [])
    
    # Предпросмотр поста
    preview_text = "👁‍🗨 *Предпросмотр поста:*\n\n" + (post_text if post_text else "(без текста)")
    preview_text += ("\n\n📎 Медиа вложений: " if lang == 'ru' else "\n\n📎 Media attachments: ") + str(len(post_media))
    
    await message.answer(preview_text, parse_mode=ParseMode.MARKDOWN)
    
    # Отправляем медиа (если есть)
    if post_media:
        media_group = MediaGroupBuilder(caption=post_text if post_text else None)
        for media_type, media_id in post_media:
            if media_type == 'photo':
                media_group.add_photo(media=media_id)
            elif media_type == 'video':
                media_group.add_video(media=media_id)
            elif media_type == 'document':
                media_group.add_document(media=media_id)
        
        await message.answer_media_group(media_group.build())
    
    # Кнопки подтверждения
    builder = ReplyKeyboardBuilder()
    if lang == 'ru':
        builder.add(KeyboardButton(text="✅ Опубликовать"), KeyboardButton(text="❌ Отменить"))
    else:
        builder.add(KeyboardButton(text="✅ Publish"), KeyboardButton(text="❌ Cancel"))
    builder.adjust(1)
    
    await state.set_state(Form.post_confirm)
    await message.answer(
        "Подтвердите публикацию этого поста" if lang == 'ru'
        else "Confirm publishing this post",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@dp.message(Form.post_confirm, lambda message: message.text in ["✅ Опубликовать", "✅ Publish"])
async def publish_post(message: Message, state: FSMContext):
    data = await state.get_data()
    post_text = data.get('post_text', '')
    post_media = data.get('post_media', [])
    post_lang = data.get('post_language', 'ru')  # Получаем язык поста
    lang = get_user_lang(message.from_user.id)

    success = 0
    failures = 0

    # Фильтруем пользователей по языку
    target_users = {
        user_id: user_data 
        for user_id, user_data in db.data.items() 
        if user_data.get('language') == post_lang
    }

    if not target_users:
        await message.answer(
            "❌ Нет пользователей с выбранным языком!" if lang == 'ru' 
            else "❌ No users with selected language!",
            reply_markup=create_admin_keyboard(lang)
        )
        await state.clear()
        return

    # Рассылка только отфильтрованным пользователям
    for user_id in target_users:
        try:
            if post_media:
                media_group = MediaGroupBuilder(caption=post_text if post_text else None)
                for media_type, media_id in post_media:
                    if media_type == 'photo':
                        media_group.add_photo(media=media_id)
                    elif media_type == 'video':
                        media_group.add_video(media=media_id)
                    elif media_type == 'document':
                        media_group.add_document(media=media_id)
                
                await bot.send_media_group(user_id, media_group.build())
            else:
                await bot.send_message(user_id, post_text)
            
            success += 1
        except Exception as e:
            failures += 1
            logger.error(f"Ошибка отправки пользователю {user_id}: {e}")

    await message.answer(
        f"📢 Пост опубликован для {post_lang.upper()} аудитории!\n"
        f"• Успешно: {success}\n"
        f"• Ошибок: {failures}"
        if lang == 'ru' else 
        f"📢 Post published for {post_lang.upper()} audience!\n"
        f"• Success: {success}\n"
        f"• Failures: {failures}"
    )
    
    await state.clear()

@dp.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Обработчик команды отмены"""
    await state.clear()
    lang = get_user_lang(message.from_user.id)
    if await is_admin(message.from_user.id):
        await show_admin_panel(message.from_user.id, lang)

@dp.message(Command("backup"))
async def cmd_backup(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
    shutil.copy2(db.filename, backup_name)
    
    with open(backup_name, 'rb') as f:
        await message.answer_document(f, caption="Резервная копия базы")
    
backup_files = glob.glob("backup_*.pkl")
for file in backup_files:
    if os.stat(file).st_mtime < (time.time() - 7 * 86400):
        os.remove(file)
        logger.info(f"Удален старый бэкап: {file}")

async def main():
    """Запуск бота"""
    await dp.start_polling(bot)



if __name__ == '__main__':
    asyncio.run(main())
