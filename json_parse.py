# import os
import redis
import json


def parse_json(user_info,chat_id, question_number,messanger_name):
    user_info = json.loads(user_info)
    user_info[f"user_{messanger_name}_{chat_id}"] = {"last_asked_question": question_number}
    user_info_json = json.dumps(user_info)
    return user_info_json
