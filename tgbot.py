import os
import random
from enum import Enum, auto
from functools import partial

import redis
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from questions_and_answers import get_answer_questions

# ASK_QUESTION, CHECK_ANSWER, = range(3)

class Handlers(Enum):
    ASK_QUESTION = auto()
    CHECK_ANSWER = auto()
    SURRENDERED = auto()


def create_tg_keyboard():
    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    return reply_markup


def handle_new_question_request(connect_to_redis, update, context):
    chat_id = update.effective_chat.id
    questions = get_answer_questions()
    question = random.choice(list(questions))
    context.bot.send_message(
        chat_id=chat_id,
        text=question,
        reply_markup=create_tg_keyboard()
    )
    connect_to_redis.set(chat_id, question)
    return Handlers.CHECK_ANSWER


def handle_solution_attempt(connect_to_redis, update, context):
    questions = get_answer_questions()
    chat_id = update.effective_chat.id

    if update.message.text.split(".")[0] in questions.get(connect_to_redis.get(chat_id)):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Правильно! Поздравляю! Для следующего вопроса нажми "Новый вопрос"',
            reply_markup=create_tg_keyboard(),
        )
        return Handlers.ASK_QUESTION
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Неправильно, Попробуешь ещё раз?',
            reply_markup=create_tg_keyboard()
        )
        return Handlers.CHECK_ANSWER


def hadle_surrendered(connect_to_redis, update, context):
    chat_id = update.effective_chat.id
    questions = get_answer_questions()
    question = random.choice(list(questions))
    context.bot.send_message(
        chat_id=chat_id,
        text=f"Вот тебе правильный ответ: {questions.get(connect_to_redis.get(chat_id))}\n\n"
             f'Что бы продолжить нажми "Новый вопрос"',
    )
    return Handlers.ASK_QUESTION


def cancel(update, context):
    update.message.reply_text('Всего хорошего!.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! я бот для викторин!",
                             reply_markup=create_tg_keyboard())
    return Handlers.ASK_QUESTION


def main():
    load_dotenv()

    tg_token = os.getenv('TG_TOKEN')
    redis_address = os.getenv('REDIS_ADRESS')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDiS_PASSWORD')

    connect_to_redis = redis.Redis(host=redis_address, port=redis_port, password=redis_password, decode_responses=True)

    updater = Updater(token=tg_token, use_context=True)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={

            Handlers.ASK_QUESTION: [MessageHandler(Filters.text & (~Filters.command),
                                                   partial(handle_new_question_request, connect_to_redis))],

            Handlers.CHECK_ANSWER: [
                MessageHandler(Filters.text('Сдаться'), partial(hadle_surrendered, connect_to_redis)),
                MessageHandler(Filters.text & (~Filters.command), partial(handle_solution_attempt, connect_to_redis)),

            ],

        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    updater.dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
