from flask import Flask, render_template
import requests

app = Flask(__name__)

BOOKS_URL = "https://drive.google.com/uc?export=download&id=1GwKEkGCxFPwV1HIl37bKZMofoPypNZfY"


@app.route("/")
def home():
    try:
        response = requests.get(BOOKS_URL, timeout=10)
        response.raise_for_status()
        books = response.json()
    except Exception as e:
        print("Error loading books:", e)
        books = []

    return render_template("index.html", books=books)


if __name__ == "__main__":
    app.run(debug=True)
