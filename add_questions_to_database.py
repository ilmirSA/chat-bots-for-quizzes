import argparse
import json
import os

import redis
from colorama import Fore
from colorama import init
from dotenv import load_dotenv


def parse_questions(path_to_folder):
    file_path = os.listdir(path_to_folder)

    if len(file_path) == 0:
        raise FileNotFoundError

    answer_on_questions = {}
    for file_name in file_path:
        with open(f'{path_to_folder}/{file_name}', 'r', encoding='KOI8-R') as file:
            file_content = file.read().split("\n\n")
        question = ''

        for text in file_content:

            if 'Вопрос' in text:

                split_text = text.split('\n')
                delete_word = split_text.pop(0)
                question = " ".join(split_text)


            elif "Ответ:" in text:
                answer = text.split("\n")[1]
                answer_on_questions.update({question: answer})

    return answer_on_questions


def add_to_redis(connect_to_redis, questions):
    redis_questions = {}
    count = 1
    for question, answer, in questions.items():
        n = f'question_{count}'
        redis_questions[n] = {'question': question,
                              'answer': answer
                              }
        count += 1

    questions_info = json.dumps(redis_questions)
    connect_to_redis.set('questions', questions_info)


def main():
    init()
    load_dotenv()
    try:
        parser = argparse.ArgumentParser(description='Скрипт добавляет вопросы из файла в базу данных Redis')
        parser.add_argument('-p', '--path_folder', help='Укажите путь до папки с вопросами')
        questions = parse_questions(parser.parse_args().path_folder)
        redis_address = os.getenv('REDIS_ADRESS')
        redis_port = os.getenv('REDIS_PORT')
        redis_password = os.getenv('REDiS_PASSWORD')
        connect_to_redis = redis.Redis(host=redis_address, port=redis_port, password=redis_password,
                                       decode_responses=True)
        add_to_redis(connect_to_redis, questions)
        print(Fore.GREEN + "Вопросы добавленыв базу успешно! ")
    except FileNotFoundError:
        print(Fore.RED + "Не удалось найти папку или папка пустая!")


if __name__ == '__main__':
    main()
