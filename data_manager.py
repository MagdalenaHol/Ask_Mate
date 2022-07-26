from werkzeug.utils import secure_filename
import os
import database_common
import util
import bcrypt

BASEPATH = os.path.dirname(os.path.abspath(__file__)) + '/'
ALLOWED_EXTENSIONS = {'jpg', 'png'}
UPLOAD_FOLDER = 'sample_data/uploads'


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_for_available_filename(filename):
    if os.path.isfile(BASEPATH + UPLOAD_FOLDER + f'/{filename}'):
        file_suffix = os.urandom(10).hex()
        filename = filename.split(".")
        return check_for_available_filename(f'{filename[0]}{file_suffix}.{filename[1]}')
    else:
        return filename


def save_image(file):
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = check_for_available_filename(filename)
        file.save(os.path.join(BASEPATH + UPLOAD_FOLDER, filename))
        return filename


@database_common.connection_handler
def get_all_questions(cursor):
    query = """
        SELECT *
        FROM question
        ORDER BY submission_time"""
    cursor.execute(query)
    return cursor.fetchall()


@database_common.connection_handler
def get_last_question(cursor):
    query = """
        SELECT *
        FROM question
        ORDER BY submission_time DESC"""
    cursor.execute(query)
    return cursor.fetchone()


@database_common.connection_handler
def add_question_to_database(cursor, question):
    query = """
        INSERT INTO question (submission_time, view_number, vote_number, title, message, image, user_id)
        VALUES (current_timestamp, 0, 0, %(title)s, %(message)s, %(image)s,%(user_id)s) """
    cursor.execute(query, {'title': question['title'],
                           'message': question['message'],
                           'image': question['image'],
                           'user_id': question['user_id']})
    question = get_last_question()
    return question['id']


@database_common.connection_handler
def add_answer_to_database(cursor, answer):
    query = """
        INSERT INTO answer (submission_time, vote_number, question_id, message, image, user_id)
        VALUES (current_timestamp, 0, %(question_id)s, %(message)s, %(image)s, %(user_id)s)"""
    cursor.execute(query, {'question_id': answer['question_id'],
                           'message': answer['message'],
                           'image': answer['image'],
                           'user_id': answer['user_id']})


@database_common.connection_handler
def get_question(cursor, question_id):
    query = """
        SELECT *
        FROM question
        WHERE id = %(question_id)s"""
    cursor.execute(query, {'question_id': question_id})
    return cursor.fetchone()


@database_common.connection_handler
def get_answer(cursor, answer_id):
    query = """
        SELECT *
        FROM answer
        WHERE id = %(answer_id)s"""
    cursor.execute(query, {'answer_id': answer_id})
    return cursor.fetchone()


@database_common.connection_handler
def get_answers_for_question(cursor, question_id):
    query = """
        SELECT *
        FROM answer
        WHERE question_id = %(question_id)s"""
    cursor.execute(query, {'question_id': question_id})
    return cursor.fetchall()


@database_common.connection_handler
def get_last_answer(cursor):
    query = """
        SELECT *
        FROM answer
        ORDER BY submission_time DESC"""
    cursor.execute(query)
    return cursor.fetchone()


@database_common.connection_handler
def update_question_in_database(cursor, question):
    query = """
        UPDATE question
        SET title = %(title)s,
        message = %(message)s,
        view_number = %(view_number)s,
        vote_number = %(vote_number)s,
        image = %(image)s
        WHERE id = %(question_id)s"""
    cursor.execute(query, {'title': question['title'],
                           'message': question['message'],
                           'view_number': question['view_number'],
                           'vote_number': question['vote_number'],
                           'image': question['image'],
                           'question_id': question['id']})


@database_common.connection_handler
def update_answer_in_database(cursor, answer):
    query = """
        UPDATE answer
        SET message = %(message)s,
        vote_number = %(vote_number)s,
        image = %(image)s
        WHERE id = %(answer_id)s"""
    cursor.execute(query, {'message': answer['message'],
                           'vote_number': answer['vote_number'],
                           'image': answer['image'],
                           'answer_id': answer['id']})


@database_common.connection_handler
def delete_all_answers(cursor, question_id):
    answers = get_answers_for_question(question_id)
    for answer in answers:
        util.delete_file(answer)

    query = """
        DELETE
        FROM answer
        WHERE question_id = %(question_id)s"""
    cursor.execute(query, {'question_id': question_id})


@database_common.connection_handler
def delete_question(cursor, question_id):
    question = get_question(question_id)
    util.delete_file(question)
    remove_all_tags_from_question(question_id)
    comments = get_comments_for_question(question_id)
    for comment in comments:
        remove_comment(comment['id'])
    delete_all_answers(question_id)
    query = """
        DELETE
        FROM question
        WHERE id = %(question_id)s"""
    cursor.execute(query, {'question_id': question_id})


@database_common.connection_handler
def delete_answer(cursor, answer_id):
    answer = get_answer(answer_id)
    comments = get_comments_by_answer_id(answer_id)
    for comment in comments:
        remove_comment(comment['id'])
    util.delete_file(answer)
    query = """
        SELECT *
        FROM question
        WHERE id = %(question_id)s"""
    cursor.execute(query, {'question_id': answer['question_id']})
    question = cursor.fetchone()

    query = """
        DELETE
        FROM answer
        WHERE id = %(answer_id)s"""
    cursor.execute(query, {'answer_id': answer_id})

    return question['id']


@database_common.connection_handler
def get_tags_for_question(cursor, question_id):
    tags = []
    query = """
        SELECT tag_id
        FROM question_tag
        WHERE question_id = %(question_id)s"""
    cursor.execute(query, {'question_id': question_id})
    tag_ids = cursor.fetchall()
    query = """
        SELECT name
        FROM tag
        WHERE id = %(tag_id)s"""
    for tag_id in tag_ids:
        cursor.execute(query, {'tag_id': tag_id['tag_id']})
        tags.append(cursor.fetchone())
    question_tags = {tag['name'] for tag in tags}
    return sorted(list(question_tags))


@database_common.connection_handler
def get_all_tags(cursor):
    query = """
        SELECT name
        FROM tag"""
    cursor.execute(query)
    all_tags = cursor.fetchall()
    tags = {tag['name'] for tag in all_tags}
    return sorted(list(tags))


@database_common.connection_handler
def remove_all_tags_from_question(cursor, question_id):
    query = """
        DELETE
        FROM question_tag
        WHERE question_id = %(question_id)s"""
    cursor.execute(query, {'question_id': question_id})


@database_common.connection_handler
def get_tag_id(cursor, tag):
    query = """
        SELECT id
        FROM tag
        WHERE name = %(tag)s"""
    cursor.execute(query, {'tag': tag})
    return cursor.fetchone()


@database_common.connection_handler
def add_tag_to_question(cursor, question_id, tag_id):
    query = """
        INSERT INTO question_tag
        VALUES (%(question_id)s, %(tag_id)s)"""
    cursor.execute(query, {'question_id': question_id, 'tag_id': tag_id})


def update_tags_for_question(question_id, tags):
    remove_all_tags_from_question(question_id)
    tag_ids = [get_tag_id(tag)['id'] for tag in tags]
    for tag_id in tag_ids:
        add_tag_to_question(question_id, tag_id)


@database_common.connection_handler
def add_new_tag(cursor, tag):
    query = """
        INSERT INTO tag (name)
        VALUES (%(tag)s)"""
    cursor.execute(query, {'tag': tag})


def get_tags_with_ids():
    tags_with_id = dict()
    tags = get_all_tags()
    for tag in tags:
        tags_with_id[tag] = get_tag_id(tag)
    return tags_with_id


@database_common.connection_handler
def remove_tag_from_question(cursor, question_id, tag_id):
    query = """
        DELETE
        FROM question_tag
        WHERE question_id = %(question_id)s AND tag_id = %(tag_id)s"""
    cursor.execute(query, {'question_id': question_id, 'tag_id': tag_id})


@database_common.connection_handler
def get_latest_questions(cursor):
    query = """
        SELECT title, id
        FROM question
        ORDER BY id DESC 
        LIMIT 5 """
    cursor.execute(query)
    return cursor.fetchall()


@database_common.connection_handler
def add_comment_to_database(cursor, comment):
    query = """
        INSERT INTO comment (question_id, answer_id, message, submission_time, edited_count, user_id)
        VALUES (%(question_id)s, %(answer_id)s, %(message)s, current_timestamp, 0, %(user_id)s)"""
    cursor.execute(query, {'question_id': comment['question_id'],
                           'answer_id': comment['answer_id'],
                           'message': comment['message'],
                           'user_id': comment['user_id']
                           })


@database_common.connection_handler
def get_comments_for_question(cursor, question_id):
    query = """
        SELECT *
        FROM comment
        WHERE question_id = %(question_id)s"""
    cursor.execute(query, {'question_id': question_id})
    return cursor.fetchall()


@database_common.connection_handler
def remove_comment(cursor, comment_id):
    query = """
        DELETE
        FROM comment
        WHERE id = %(comment_id)s"""
    cursor.execute(query, {'comment_id': comment_id})


@database_common.connection_handler
def search_questions_in_db(cursor, search_phrase):
    query = """
        SELECT *
        FROM question
        WHERE title ILIKE %(phrase)s
        OR message ILIKE %(phrase)s
        """
    cursor.execute(query, {'phrase': f'%{search_phrase}%'})
    return cursor.fetchall()


@database_common.connection_handler
def search_answers_in_db(cursor, search_phrase):
    query = """
        SELECT *
        FROM answer
        WHERE message ILIKE %(phrase)s
        """
    cursor.execute(query, {'phrase': f'%{search_phrase}%'})
    return cursor.fetchall()


@database_common.connection_handler
def get_comment_by_comment_id(cursor, comment_id):
    query = """
        SELECT *
        FROM comment
        WHERE id = %(comment_id)s"""
    cursor.execute(query, {'comment_id': comment_id})
    return cursor.fetchone()


@database_common.connection_handler
def get_last_added_comment(cursor):
    query = """
        SELECT *
        FROM comment
        ORDER BY submission_time DESC"""
    cursor.execute(query)
    return cursor.fetchone()


@database_common.connection_handler
def get_comments_by_answer_id(cursor, answer_id):
    query = """
        SELECT *
        FROM comment
        WHERE answer_id = %(answer_id)s"""
    cursor.execute(query, {'answer_id': answer_id})
    return cursor.fetchall()


@database_common.connection_handler
def update_comment_in_database(cursor, comment):
    query = """
        UPDATE comment
        SET message = %(message)s,
        submission_time = current_timestamp,
        edited_count = edited_count + %(edited_count)s
        WHERE id = %(comment_id)s"""
    cursor.execute(query, {'comment_id': comment['id'],
                           'message': comment['message'],
                           'edited_count': comment['edited_count']})


@database_common.connection_handler
def add_user(cursor, user):
    query = """
        INSERT INTO users(username, password, registration_time, reputation)
        VALUES (%(username)s, %(password)s, current_timestamp, 0)"""
    cursor.execute(query, {'username': user['username'], 'password': user['password']})


@database_common.connection_handler
def check_if_user_exists(cursor, username):
    query = """
        SELECT username
        FROM users
        WHERE username = %(username)s"""
    cursor.execute(query, {'username': username})
    return cursor.fetchone()


def hash_password(plain_text_password):
    hashed_bytes = bcrypt.hashpw(plain_text_password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')


def verify_password(plain_text_password, hashed_password):
    hashed_bytes_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_text_password.encode('utf-8'), hashed_bytes_password)


@database_common.connection_handler
def get_user_password(cursor, user_email):
    query = """
        SELECT password
        FROM users
        WHERE username = %(username)s"""
    cursor.execute(query, {'username': user_email})
    user = cursor.fetchone()
    if user:
        return user.get('password')


@database_common.connection_handler
def get_user_details(cursor, user_email=None):
    if user_email is None:
        user_email = util.current_user()
    query = """
        SELECT *
        FROM users
        WHERE username = %(username)s"""
    cursor.execute(query, {'username': user_email})
    return cursor.fetchone()


@database_common.connection_handler
def get_questions_from_user(cursor, user_email):
    query = """
        SELECT question.id, question.title, question.message
        FROM users
        JOIN question on users.id = question.user_id
        WHERE users.username = %(username)s"""
    cursor.execute(query, {'username': user_email})
    return cursor.fetchall()


@database_common.connection_handler
def get_answers_and_question_titles_from_user(cursor, user_email):
    query = """
        SELECT answer.question_id, answer.message, question.title
        FROM users
        JOIN answer on users.id = answer.user_id
        JOIN question on answer.question_id = question.id
        WHERE users.username = %(username)s"""
    cursor.execute(query, {'username': user_email})
    return cursor.fetchall()


@database_common.connection_handler
def get_comments_and_question_ids_from_user(cursor, user_email):
    query = """
        SELECT comment.message, comment.question_id
        FROM users
        JOIN comment on users.id = comment.user_id
        WHERE users.username = %(username)s"""
    cursor.execute(query, {'username': user_email})
    return cursor.fetchall()


@database_common.connection_handler
def accept_answer(cursor, question_id, answer_id):
    query = """
        UPDATE question
        SET accepted_answer = %(answer_id)s
        WHERE id = %(question_id)s"""
    cursor.execute(query, {'question_id': question_id,
                           'answer_id': answer_id})


@database_common.connection_handler
def get_users(cursor):
    query = """
        SELECT id, username, reputation, registration_time::DATE AS registration_date
        FROM users
        ORDER BY id"""
    cursor.execute(query)
    return cursor.fetchall()


@database_common.connection_handler
def get_number_of_data(cursor, author_id, data):
    query = f"""
        SELECT COUNT(*) AS number_of_{data}s
        FROM {data}
        WHERE user_id = %(user_id)s"""
    cursor.execute(query, {'user_id': author_id})
    return cursor.fetchone()[f'number_of_{data}s']


@database_common.connection_handler
def get_user_details_by_id(cursor, user_id):
    query = """
        SELECT *
        FROM users
        WHERE id = %(id)s"""
    cursor.execute(query, {'id': user_id})
    return cursor.fetchone()


@database_common.connection_handler
def get_tag(cursor):
    query = """
    SELECT *
    FROM tag
    """
    cursor.execute(query)
    return cursor.fetchall()


@database_common.connection_handler
def get_number_of_questions_assign_to_tag(cursor, tag_id):
    query = """
    SELECT COUNT(*) AS number_of_tagged_question
    FROM question_tag
    WHERE tag_id = %(tag_id)s """
    cursor.execute(query, {'tag_id': tag_id})
    return cursor.fetchone()['number_of_tagged_question']


@database_common.connection_handler
def change_reputation(cursor, user_id, reputation_change):
    query = """
    UPDATE users
    SET reputation = reputation + %(change)s
    WHERE id = %(id)s"""
    cursor.execute(query, {'change': reputation_change,
                           'id': user_id})


@database_common.connection_handler
def get_post_author_by_post_id(cursor, id, table):
    query = f"""
    SELECT users.username AS username
    FROM users
    JOIN {table}
    ON users.id = {table}.user_id
    WHERE {table}.id = %(id)s
    """
    cursor.execute(query, {'id': id})
    return cursor.fetchone()['username']
    

