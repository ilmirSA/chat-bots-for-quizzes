import json
import os

import redis
import vk_api
from dotenv import load_dotenv
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from collect_data import collect_data
from get_answer import get_answer
from get_random_question import get_question


def keyboard():
    keyboard = VkKeyboard(one_time=True)

    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)

    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.POSITIVE)

    return keyboard.get_keyboard()


def start(event, vk_method):
    user_id = event.obj['message']['from_id']
    message = 'Приветсвуем тебя в нашкй викторине!что бы начать нажми на кнопку "Новый вопрос"'
    random_id = get_random_id()
    send_message(event, vk_method, user_id, message)


def ask_question(event, vk_method, connect_to_redis):
    user_id = event.obj['message']['from_id']

    correct_user_responses = f'correct_user_responses{user_id}'
    incorrect_user_responses = f'incorrect_user_responses{user_id}'

    if not connect_to_redis.get(correct_user_responses):
        connect_to_redis.set(correct_user_responses, 0)
        connect_to_redis.set(incorrect_user_responses, 0)

    question, question_number = get_question(connect_to_redis)
    if not connect_to_redis.get('users'):
        user_tg_info = {f'user_vk_{user_id}': {'last_asked_question': question_number}}
        user_tg_info_json = json.dumps(user_tg_info)
        connect_to_redis.set('users', user_tg_info_json)

    send_message(event, vk_method, user_id, question)
    users_vk_info = json.loads(connect_to_redis.get('users'))
    user_name_key = f"user_vk_{user_id}"
    user_value = {"last_asked_question": question_number}

    users_vk_info[user_name_key] = user_value

    users_vk_info_json = json.dumps(users_vk_info)

    connect_to_redis.set('users', users_vk_info_json)


def response_check(event, vk_method, connect_to_redis):
    user_id = event.obj['message']['from_id']

    answer = get_answer(connect_to_redis, user_id, 'vk')

    correct_user_responses_info = f'correct_user_responses{user_id}'
    incorrect_user_responses_info = f'incorrect_user_responses{user_id}'

    if event.obj['message']['text'].split('.')[0] in answer:
        message = 'Правильно!Поздравляю!Для следующего вопроса нажми на кнопку "Новый вопрос"',
        send_message(event, vk_method, user_id, message)
        connect_to_redis.incr(correct_user_responses_info)
    else:
        message = 'Не правильно! Попробуешь ещё раз?',
        send_message(event, vk_method, user_id, message)
        connect_to_redis.incr(incorrect_user_responses_info)


def issue_an_answer(event, vk_method, connect_to_redis):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Вопрос составлен неверно', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)

    user_id = event.obj['message']['from_id']

    answer = get_answer(connect_to_redis, user_id, 'vk')
    message = f'Вот тебе правильный ответ: {answer}. Что бы продолжить нажми на кнопку "Новый вопрос"'
    vk_method.messages.send(
        user_id=user_id,
        message=message,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard()
    )


def send_message(event, vk_method, user_id, message):
    vk_method.messages.send(
        user_id=user_id,
        message=message,
        random_id=get_random_id(),
        keyboard=keyboard()
    )


def show_score(event, vk_method, connect_to_redis):
    user_id = event.obj['message']['from_id']

    right_answers = connect_to_redis.get(f'correct_user_responses{user_id}')
    wrong_answers = connect_to_redis.get(f'incorrect_user_responses{user_id}')
    message = f'''Количество правильных ответов : {right_answers} Количество не правильных : {wrong_answers} Что бы продолжить нажми на кнопку "Новый вопрос" '''
    send_message(event, vk_method, user_id, message)


def main():
    load_dotenv()
    vk_token = os.getenv('VK_TOKEN')
    vk_group_id = os.getenv('VK_GROUP_ID')

    vk_session = vk_api.VkApi(token=vk_token)
    vk_method = vk_session.get_api()
    redis_address = os.getenv('REDIS_ADRESS')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDiS_PASSWORD')

    connect_to_redis = redis.Redis(host=redis_address, port=redis_port, password=redis_password, decode_responses=True)
    longpoll = VkBotLongPoll(vk_session, group_id=vk_group_id)
    while True:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                if event.obj['message']['text'] in ['Привет', 'Начать', 'привет', 'начать']:
                    start(event, vk_method)

                elif event.obj['message']['text'] == 'Новый вопрос':
                    ask_question(event, vk_method, connect_to_redis)
                elif event.obj['message']['text'] == 'Сдаться':
                    issue_an_answer(event, vk_method, connect_to_redis, )
                elif event.obj['message']['text'] == 'Мой счет':
                    show_score(event, vk_method, connect_to_redis)
                else:
                    response_check(event, vk_method, connect_to_redis)


if __name__ == '__main__':
    main()
