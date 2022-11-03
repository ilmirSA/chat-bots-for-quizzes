def collect_data(chat_id, question_number, messanger_name):
    user_name_key = f"user_{messanger_name}_{chat_id}"
    user_value = {"last_asked_question": question_number}
    return user_name_key, user_value
