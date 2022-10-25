import os
import random

import redis
import vk_api
from dotenv import load_dotenv
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from questions_and_answers import get_answer_questions


def keyboard():
    keyboard = VkKeyboard(one_time=True)

    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)

    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.POSITIVE)

    return keyboard.get_keyboard()


def start(event, vk_method):
    user_id = event.obj['message']['from_id']
    message = "Приветсвуем тебя в нашкй викторине!что бы начать нажми на кнопку 'Новый вопрос'`"
    random_id = get_random_id()
    send_message(event, vk_method, user_id, message)


def ask_question(event, vk_method, connect_to_redis, questions):
    question = random.choice(list(questions))
    user_id = event.obj['message']['from_id']
    send_message(event, vk_method, user_id, question)
    connect_to_redis.set(user_id, question)


def response_check(event, vk_method, questions, connect_to_redis):
    user_id = event.obj['message']['from_id']

    if questions.get(connect_to_redis.get(user_id)) == event.obj['message']['text']:
        message = "Правильно!Поздравляю!Для следующего вопроса нажми на кнопку 'Новый вопрос'",
        send_message(event, vk_method, user_id, message)
    else:
        message = "Не правильно! Попробуешь ещё раз?",
        send_message(event, vk_method, user_id, message)


def issue_an_answer(event, vk_method, connect_to_redis, questions):
    user_id = event.obj['message']['from_id']
    answer = questions.get(connect_to_redis.get(user_id))
    message = f"Вот тебе правильный ответ: {answer}. Что бы продолжить нажми на кнопку 'Новый вопрос'",
    send_message(event, vk_method, user_id, message)


def send_message(event, vk_method, user_id, message):
    vk_method.messages.send(
        user_id=user_id,
        message=message,
        random_id=get_random_id(),
        keyboard=keyboard()
    )


def main():
    load_dotenv()
    vk_token = os.getenv("VK_TOKEN")
    vk_group_id = os.getenv("VK_GROUP_ID")

    vk_session = vk_api.VkApi(token=vk_token)
    vk_method = vk_session.get_api()
    redis_address = os.getenv('REDIS_ADRESS')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDiS_PASSWORD')
    questions = get_answer_questions()
    connect_to_redis = redis.Redis(host=redis_address, port=redis_port, password=redis_password, decode_responses=True)
    longpoll = VkBotLongPoll(vk_session, group_id=vk_group_id)
    while True:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                if event.obj['message']['text'] in ['Привет', 'Начать', 'привет','начать']:
                    start(event, vk_method, keyboard)

                elif event.obj['message']['text'] == 'Новый вопрос':
                    ask_question(event, vk_method, connect_to_redis, questions)

                elif event.obj['message']['text'] == 'Сдаться':
                    issue_an_answer(event, vk_method, connect_to_redis, questions)
                else:
                    response_check(event, vk_method, questions, connect_to_redis)


if __name__ == '__main__':
    main()
