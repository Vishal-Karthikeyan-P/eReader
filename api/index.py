from flask import Flask, render_template
import requests
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, template_folder=TEMPLATE_DIR)

BOOKS_URL = "https://drive.google.com/uc?export=download&id=1GwKEkGCxFPwV1HIl37bKZMofoPypNZfY"


@app.route("/")
def home():
    try:
        response = requests.get(BOOKS_URL, timeout=10)
        response.raise_for_status()

        books = response.json()

    except Exception as e:
        print("ERROR LOADING BOOKS:", str(e))
        books = []

    return render_template("index.html", books=books)
