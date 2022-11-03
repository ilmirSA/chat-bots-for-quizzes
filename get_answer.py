import json


def get_answer(connect_to_redis, user_id, messanger_name):
    user_last_question = json.loads(connect_to_redis.get('users'))[f'user_{messanger_name}_{user_id}'][
        'last_asked_question']
    answer_to_the_question = json.loads(connect_to_redis.get('questions'))[user_last_question]['answer']
    return answer_to_the_question
