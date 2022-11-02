import redis
import json
import random

def get_questions(connect_to_redis):
    get_questions = connect_to_redis.get('questions')
    questions = json.loads(get_questions)
    question_number = random.choice(list(questions))
    question = questions.get(question_number)['question']
    return question,question_number