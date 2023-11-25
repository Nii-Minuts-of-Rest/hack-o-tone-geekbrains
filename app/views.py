import io

from flask import render_template, request, redirect, url_for
from app import app
import psycopg2

import speech_recognition as sr
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter
import ffmpeg
import re
import pymorphy3

from werkzeug.utils import secure_filename
import os


## Лемматизация текста
def lemmatize_text(lemmatizer, tokens):
    text_lem = ""
    txt = tokens.split()
    for word in txt:
        word = lemmatizer.parse(word.lower())
        text_lem += word[0].normal_form.lower()
        text_lem += " "
    return text_lem


def add_punctuation(text):
    """
    Adds punctuation to a text based on simple heuristics.
    """
    # Adding periods before capital letters (not proper nouns)
    text = re.sub(r"(\s)([А-ЯЁ][а-яё]+)", r".\1\2", text)

    # Adding commas before 'и' (and) and in other common places
    text = re.sub(r"(\s)и(\s)", r", и ", text)

    # Heuristic for other common places for commas
    common_phrases = ['также', 'например', 'как', 'что', 'если', 'но', 'так что', 'потому что']
    for phrase in common_phrases:
        text = re.sub(r"(\s)({})(\s)".format(phrase), r", \2 ", text)

    # Fixing the issue of multiple periods
    text = text.replace("..", ".").strip()

    return text


def process_text(text):
    """
    Processes the text, applying different rules for punctuation.
    """
    processed_text = add_punctuation(text)

    # Ensuring the text starts with a capital letter
    if processed_text:
        processed_text = processed_text[0].upper() + processed_text[1:]

    return processed_text


def extract_keywords(text):
    nltk.download('punkt')
    nltk.download('stopwords')
    tokens = word_tokenize(text, language="russian")
    filtered_tokens = [word for word in tokens if word.isalpha() and word.lower() not in stopwords.words('russian')]
    keyword_freq = Counter(filtered_tokens)
    return keyword_freq.most_common(10)


def speech_to_text(FILE):
    recognizer = sr.Recognizer()
    full_text = ""
    duration = 30  # Длительность сегмента в секундах

    # Определение длины аудиофайла
    with sr.AudioFile(FILE) as source:
        file_duration = source.DURATION

    with sr.AudioFile(FILE) as source:
        for start in range(0, int(file_duration), duration):
            try:
                audio_data = recognizer.record(source, duration=duration)
                text = recognizer.recognize_google(audio_data, language="ru-RU")
                full_text += text + " "

                # Показ прогресса обработки
                progress = (start / file_duration) * 100
                print(f"Прогресс: {progress:.2f}%")
            except sr.UnknownValueError:
                print("Не удалось распознать речь в одном из сегментов.")
            except sr.RequestError:
                print("Ошибка запроса к сервису распознавания речи.")
                break
            except EOFError:
                break
    return full_text


def get_db_connection():
    conn = psycopg2.connect(host='localhost',
                            database='Knowlage_Base',
                            user='postgres',
                            password='12345678',
                            port=5432)
    return conn

@app.route('/')
@app.route('/index')
def index():
    return render_template("upload.html")


@app.route('/processing', methods = ['GET', 'POST'])
def processing():
    print("Hello world")
    print(request.url)
    print(request.files)
    if request.method == 'POST':
        print("Hello world")
        # check if the post request has the file part
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']

        #mp3_name = ".\\tmp.mp3"
        wav_name = ".\\tmp.wav"
        wav_data = file.read()
        #mp3_data = file.read()
        with open(wav_name, 'wb') as f:
            f.write(wav_data)

        #Sleep(100)


        ### SOME PROCESSING HERE

        text = speech_to_text(wav_name)
        punctuated_text = process_text(text)

        Name = "Текст наполнитель в Веб-дизайне"

        TERMS = [('Веб-дизайн', 'Дизайн страниц для интернета'), ('Текст-рыба', 'текст несущий малую смысловую нагрузку, используется для просмотра того, как выглядит текст на странице'), ('Ещё одно определение', 'текст ещё одного определения')]
        TEXT = punctuated_text

        LEMMATIZER = pymorphy3.MorphAnalyzer()
        LemmaText = lemmatize_text(LEMMATIZER, text)

        print(LemmaText)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT term_name, term_lemma, term_res from public.terms;')
        terms = cur.fetchall()
        cur.close()
        conn.close()
        print(terms)

        term_prod = []

        for term in terms:
            index = LemmaText.find(term[1].strip().lower())
            if index > 0:
                print(term[1].strip().lower(), "Found")
                term_prod.append((term[0], term[2]))
            else:
                print(term[1].strip().lower(), "Not Found")

        keywords = extract_keywords(LemmaText)
        print("Ключевые слова:", keywords)

        return render_template("report.html",
                               title=Name,
                               terms=term_prod,
                               text=TEXT, terms_pos=keywords)


        #dest = os.path.join(
        #    app.config['UPLOAD_FOLDER'],
        #    secure_filename(file.filename)
        #)
        #print(dest)
        #file.save(dest)
        #print(file)
    return redirect('/index')


@app.route('/200', methods=['GET'])
def successful():
    return render_template("200.html")


@app.route('/404', methods=['GET'])
def not_found():
    return render_template("404.html")


@app.route('/500', methods=['GET'])
def internal_error():
    return render_template("500.html")


@app.route('/test_db', methods=['GET'])
def test_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT VERSION();')
    version = cur.fetchall()
    print(version)
    cur.close()
    conn.close()
    return render_template("dbtest.html", version=version)


@app.route('/knowledge', methods=['GET'])
def get_terms():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT term_id, term_name, term_topic, term_tag, term_res from public.terms;')
    terms = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("knowlage_show.html", terms=terms)


@app.route('/knowledge/create',  methods = ['GET', 'POST'])
def create_term():
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor()
        term = request.form.get("termin")

        LEMMATIZER = pymorphy3.MorphAnalyzer()
        term_lemma = lemmatize_text(LEMMATIZER, term)
        term_res = request.form.get("meaning")
        cur.execute('INSERT INTO public.terms VALUES (DEFAULT, %s, %s, %s, %s, %s);', (0,0,term,term_lemma,term_res))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/knowledge')
    return render_template("termin_create.html")


@app.route('/knowledge/edit/<id>',  methods=['GET', 'POST'])
def edit_term(id):
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor()
        term = request.form.get("termin")
        LEMMATIZER = pymorphy3.MorphAnalyzer()
        term_lemma = lemmatize_text(LEMMATIZER, term)
        term_res = request.form.get("meaning")
        cur.execute('UPDATE public.terms SET term_name = %s, term_lemma = %s, term_res = %s where term_id = %s;',
                    (term, term_lemma, term_res, id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/knowledge')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT term_id, term_name, term_topic, term_tag, term_res from public.terms WHERE term_id = %s ;', (id,))
    term = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("termin_edit.html", term=term)


@app.route('/knowledge/delete/<id>',  methods=['GET'])
def delete_term(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM public.terms WHERE term_id = %s;', (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/knowledge')
