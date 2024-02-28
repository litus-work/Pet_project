import openai
import telebot
import settings
import logging
import sqlite3
from telebot import types

logging.basicConfig(level=logging.INFO)
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
bot = telebot.TeleBot(settings.TOKEN)

models = {
    "gpt-3.5-turbo-0125": "GPT-3.5 Turbo (default)",
    "gpt-3.5-turbo-0126": "GPT-3.5 Turbo (alternative)",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo-16k-0613",
    "dall-e-3": "DALL·E 3",
    "tts-1-hd": "Text-to-speech 1"
}


# Функция для открытия соединения с базой данных
def connect_to_database():
    return sqlite3.connect('context.db')


# Функция для закрытия соединения с базой данных
def close_database_connection(conn):
    conn.close()


# Создание таблицы context
def create_context_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS context (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            model TEXT
        )
    ''')
    conn.commit()


# Подключение к базе данных и создание таблицы
conn = connect_to_database()
create_context_table(conn)
close_database_connection(conn)


# Обработка команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Для начала работы введите текст.")


# Обработка команды /set_model
@bot.message_handler(commands=['set_model'])
def set_model(message):
    conn = connect_to_database()
    cursor = conn.cursor()

    keyboard = types.InlineKeyboardMarkup()
    for model_id, model_name in models.items():
        button = types.InlineKeyboardButton(text=model_name, callback_data=model_id)
        keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите модель:", reply_markup=keyboard)

    close_database_connection(conn)
    print("Закрыл базу")


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    print("Callback query received")  # Добавленный вывод
    callback_handler(call)


def callback_handler(call):
    if call.message:
        conn = connect_to_database()
        cursor = conn.cursor()

        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"Вы выбрали модель: {models.get(call.data)}")
        # Сохранение выбранной модели в базе данных
        user_id = call.from_user.id
        model = call.data
        print(user_id, model)
        try:
            print(1)
            cursor.execute('''
                       INSERT OR REPLACE INTO context (user_id, model) VALUES (?, ?)
                   ''', (user_id, model))
            conn.commit()
            print(2)
            logging.info(f"Model {model} saved for user {user_id}")
        except sqlite3.Error as e:
            print(3)
            logging.error(f"Error while saving model to database: {e}")

        close_database_connection(conn)


# Обработка выбора модели
@bot.message_handler(func=lambda _: True)
def handle_message(message):
    try:
        conn = connect_to_database()
        cursor = conn.cursor()

        logging.info(f"Received message: {message.text}")
        # Здесь нужно использовать сохраненную модель для генерации ответа
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are my helpful assistant."},
                {"role": "user", "content": message.text}
            ],
        )
        bot.send_message(chat_id=message.from_user.id, text=completion.choices[0].message.content)
        logging.info(f"Sent response: {completion.choices[0].message.content}")

        close_database_connection(conn)
    except Exception as e:
        logging.error(f"An error occurred: {e}")


if __name__ == "__main__":
    try:
        bot.polling()
    finally:
        # В конце работы бота закрываем соединение с базой данных
        close_database_connection(conn)
