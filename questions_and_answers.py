import os

def get_answer_questions():
    file_path = os.listdir('quiz-questions')
    answer_on_questions = {}
    for file_name in file_path:
        with open(f'quiz-questions/{file_name}', 'r', encoding='KOI8-R') as file:
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