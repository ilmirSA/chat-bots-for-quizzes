import json
import os
import random
from enum import Enum, auto
from functools import partial

import redis
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

ASK_QUESTION, CHECK_ANSWER, SURRENDERED = range(3)


class Handlers(Enum):
    ASK_QUESTION = auto()
    CHECK_ANSWER = auto()
    SURRENDERED = auto()
    MY_SCORE=auto()


def parse_json(connect_to_redis, user_info, chat_id, question):
    user_info = json.loads(user_info)
    user_info[f"user_tg_{chat_id}"] = {"last_asked_question": question}
    user_info_json = json.dumps(user_info)
    return user_info_json


def create_tg_keyboard():
    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    return reply_markup


def handle_new_question_request(connect_to_redis, update, context):
    chat_id = update.effective_chat.id
    get_questions = connect_to_redis.get('questions')
    questions = json.loads(get_questions)
    print(questions)
    question_number = random.choice(list(questions))
    question = questions.get(question_number)['question']
    user_counter=f'user_counter{chat_id}'
    if not connect_to_redis.get(user_counter):
        connect_to_redis.set(user_counter,0)
    context.bot.send_message(
        chat_id=chat_id,
        text=question,
        reply_markup=create_tg_keyboard()
    )
    users_info= connect_to_redis.get('users')
    user_json = parse_json(connect_to_redis, users_info, chat_id, question_number)
    connect_to_redis.set('users', user_json)



    return Handlers.CHECK_ANSWER


def handle_solution_attempt(connect_to_redis, update, context):
    chat_id = update.effective_chat.id
    user_last_question = json.loads(connect_to_redis.get('users'))[f'user_tg_{chat_id}']['last_asked_question']
    answer_to_the_question = json.loads(connect_to_redis.get('questions'))[user_last_question]['answer']
    user_counter_id= f'user_counter{chat_id}'
    if update.message.text.split(".")[0] in answer_to_the_question:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Правильно! Поздравляю! Для следующего вопроса нажми "Новый вопрос"',
            reply_markup=create_tg_keyboard(),
        )

        connect_to_redis.incr(user_counter_id)

        return Handlers.ASK_QUESTION
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Неправильно, Попробуешь ещё раз?',
            reply_markup=create_tg_keyboard()
        )
        print(connect_to_redis.get(user_counter_id))
        return Handlers.CHECK_ANSWER


def hadle_surrendered(connect_to_redis, update, context):
    chat_id = update.effective_chat.id
    user_last_question = json.loads(connect_to_redis.get('users'))[f'user_tg_{chat_id}']['last_asked_question']
    answer_to_the_question = json.loads(connect_to_redis.get('questions'))[user_last_question]['answer']

    context.bot.send_message(
        chat_id=chat_id,
        text=f"Вот тебе правильный ответ: {answer_to_the_question}\n\n"
             f'Что бы продолжить нажми "Новый вопрос"',
    )
    return Handlers.ASK_QUESTION


def show_score(connect_to_redis,update,context):
    chat_id=update.effective_chat.id
    user_score=connect_to_redis.get(f'user_counter{chat_id}')
    context.bot.send_message(
        chat_id=chat_id,
        text=f"Количество правильных ответов равняеться : {user_score} "
             f"Что бы продолжить нажми на кнопку Новый вопрос",
        reply_markup=create_tg_keyboard()
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
                MessageHandler(Filters.text & (~Filters.command),partial(handle_new_question_request, connect_to_redis)),
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
