import json
import os
from enum import Enum, auto
from functools import partial

import redis
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

from get_answer import get_answer
from get_random_questions import get_questions
from json_parse import parse_json

ASK_QUESTION, CHECK_ANSWER, SURRENDERED = range(3)


class Handlers(Enum):
    ASK_QUESTION = auto()
    CHECK_ANSWER = auto()
    SURRENDERED = auto()
    MY_SCORE = auto()


def create_tg_keyboard():
    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    return reply_markup


def handle_new_question_request(connect_to_redis, update, context):
    chat_id = update.effective_chat.id
    question, question_number = get_questions(connect_to_redis)

    correct_user_responses = f'correct_user_responses{chat_id}'
    incorrect_user_responses = f'incorrect_user_responses{chat_id}'

    if not connect_to_redis.get(correct_user_responses):
        connect_to_redis.set(correct_user_responses, 0)
        connect_to_redis.set(incorrect_user_responses, 0)

    context.bot.send_message(
        chat_id=chat_id,
        text=question,
        reply_markup=create_tg_keyboard()
    )

    if not connect_to_redis.get('all_users'):
        user_tg_info = {f'user_tg_{chat_id}': {'last_asked_question': question_number}}
        user_tg_info_json = json.dumps(user_tg_info)
        connect_to_redis.set('all_users', user_tg_info_json)

    all_users_info = connect_to_redis.get('all_users')
    user_json = parse_json(all_users_info, chat_id, question_number, 'tg')
    connect_to_redis.set('all_users', user_json)

    return Handlers.CHECK_ANSWER


def handle_solution_attempt(connect_to_redis, update, context):
    chat_id = update.effective_chat.id

    answer = get_answer(connect_to_redis, chat_id, 'tg')

    correct_user_responses_info = f'correct_user_responses{chat_id}'
    incorrect_user_responses_info = f'incorrect_user_responses{chat_id}'
    if update.message.text.split(".")[0] in answer:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Правильно! Поздравляю! Для следующего вопроса нажми "Новый вопрос"',
            reply_markup=create_tg_keyboard(),
        )

        connect_to_redis.incr(correct_user_responses_info)

        return Handlers.ASK_QUESTION
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Неправильно, Попробуешь ещё раз?',
            reply_markup=create_tg_keyboard()
        )
        connect_to_redis.incr(incorrect_user_responses_info)
        return Handlers.CHECK_ANSWER


def hadle_surrendered(connect_to_redis, update, context):
    chat_id = update.effective_chat.id
    answer = get_answer(connect_to_redis, chat_id, 'tg')

    context.bot.send_message(
        chat_id=chat_id,
        text=f'Вот тебе правильный ответ: {answer}\n\n'
             f'Что бы продолжить нажми "Новый вопрос"',
    )
    return Handlers.ASK_QUESTION


def show_score(connect_to_redis, update, context):
    chat_id = update.effective_chat.id

    right_answers = connect_to_redis.get(f'correct_user_responses{chat_id}')
    wrong_answers = connect_to_redis.get(f'incorrect_user_responses{chat_id}')
    context.bot.send_message(
        chat_id=chat_id,
        text=f'Количество правильных ответов : {right_answers} \n'
             f'Количество не правильных : {wrong_answers}\n'
             f'Что бы продолжить нажми на кнопку "Новый вопрос"',
        reply_markup=create_tg_keyboard()
    )
    return Handlers.ASK_QUESTION


def cancel(update, context):
    update.message.reply_text('Всего хорошего!.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Привет! я бот для викторин!',
                             reply_markup=create_tg_keyboard())
    return Handlers.ASK_QUESTION


def main():
    load_dotenv()
    redis_address = os.getenv('REDIS_ADRESS')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDiS_PASSWORD')
    tg_token = os.getenv('TG_TOKEN')

    connect_to_redis = redis.Redis(host=redis_address, port=redis_port, password=redis_password, decode_responses=True)

    updater = Updater(token=tg_token, use_context=True)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={

            Handlers.ASK_QUESTION: [MessageHandler(Filters.text('Мой счет'), partial(show_score, connect_to_redis)),
                                    MessageHandler(Filters.text & (~Filters.command),
                                                   partial(handle_new_question_request, connect_to_redis)),
                                    ],

            Handlers.CHECK_ANSWER: [
                MessageHandler(Filters.text('Мой счет'), partial(show_score, connect_to_redis)),
                MessageHandler(Filters.text('Сдаться'), partial(hadle_surrendered, connect_to_redis)),
                MessageHandler(Filters.text('Новый вопрос') & (~Filters.command),
                               partial(handle_new_question_request, connect_to_redis)),
                MessageHandler(Filters.text & (~Filters.command),
                               partial(handle_solution_attempt, connect_to_redis)),

            ],

        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    updater.dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
