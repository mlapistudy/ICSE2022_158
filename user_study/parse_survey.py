import pandas as pd
from collections import Counter

TEST_CASE_NUM=8
APPS = ["Q1", "Q2", "Q4", "Q5"]
V2_OUR = [False, True, False, True]

# if V2_OUR is true
MAP_true = {
    "Prefer V1": "Prefer origin", "Prefer V2": "Prefer our", "Like both": "Same", "Dislike both": "Same", 
    "Version 1 is better": "Prefer origin", "Version 2 is better": "Prefer our", "Version 1 is slightly better": "Prefer origin", "Version 2 is slightly better": "Prefer our", "No difference": "Same",
    "Definitely version 1": "Prefer origin", "Version 1": "Prefer origin", "Definitely version 2": "Prefer our", "Version 2": "Prefer our"
}
MAP_false = {
    "Prefer V2": "Prefer origin", "Prefer V1": "Prefer our", "Like both": "Same", "Dislike both": "Same", 
    "Version 2 is better": "Prefer origin", "Version 1 is better": "Prefer our", "Version 2 is slightly better": "Prefer origin", "Version 1 is slightly better": "Prefer our", "No difference": "Same",
    "Definitely version 2": "Prefer origin", "Version 2": "Prefer origin", "Definitely version 1": "Prefer our", "Version 1": "Prefer our"
}

def read_csv(file_path):
    df_data = pd.read_csv(file_path)
    df_data = df_data.fillna("")
    return df_data

def parse_test_cases(row, app, answers, test_case_num):
    for i in range(test_case_num):
        question = app + "-0_" + str(i+1)
        answer = row[question]
        answers[answer] += 1

def get_answers(all_answers, keyword):
    if keyword in all_answers.keys():
        answers = all_answers[keyword]
    else:
        answers = Counter()
        all_answers[keyword] = answers
    return answers

def mutate_answer(answer, app_no):
    if V2_OUR[app_no]:
        return MAP_true[answer]
    else:
        return MAP_false[answer]

def parse_csv(file_path):
    df_data = read_csv(file_path)
    df_data.fillna("N.A.")

    all_answers = {}
    for index, row in df_data.iterrows():
        # first two rows are not answers
        if index<=1:
            continue
        for no, app in enumerate(APPS):
            # test cases
            answers = get_answers(all_answers, app+"-0")
            for i in range(TEST_CASE_NUM):
                question = app + "-0_" + str(i+1)
                answer = row[question]
                answer = mutate_answer(answer, no)
                answers[answer] += 1
            # multiple choices + open ended question
            for i in range(1,7):
                question = app+"-"+str(i)
                answers = get_answers(all_answers, question)
                if question in row.keys():
                    answer = row[question]
                    if i==1 or i==3 or i==5:
                        answer = mutate_answer(answer, no)
                    answers[answer] += 1
    return all_answers
    
def print_answers_choice(all_answers):
    for key, value in all_answers.items():
        if key.endswith("-0"):
            print("===========================")
        output = key + "\t"
        if key.endswith("-0") or key.endswith("-1") or key.endswith("-3") or key.endswith("-5"):
            for category in ["Prefer our", "Same", "Prefer origin"]:
                output += category + "\t" + str(value[category]) + "\t"
            print(output)
        if key.endswith("-2") or key.endswith("-4"):
            for category in ["Very important", "Fairly important", "Important", "Slightly important", "Not at all important"]:
                output += category + "\t" + str(value[category]) + "\t"
            print(output)


def print_answers_text(file_path, app):
    if not app in APPS:
        print("Invalid APP name: " +str(app))
        return
    app_no = APPS.index(app)
    df_data = read_csv(file_path)
    for index, row in df_data.iterrows():
        # first two rows are not answers
        if index<=1:
            continue
        answer = row[app+"-6"]
        preference = row[app+"-5"]
        preference = mutate_answer(preference, app_no)
        print(preference +"\t"+ answer.replace("\n","."))

if __name__ == '__main__':
    file_path = "all_participants.csv"

    all_answers = parse_csv(file_path)
    print_answers_choice(all_answers)