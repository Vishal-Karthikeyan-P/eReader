from flask import Flask, render_template
import requests

app = Flask(__name__)

# Replace this with your hosted JSON URL after deployment
BOOKS_URL = "https://drive.google.com/uc?export=download&id=1GwKEkGCxFPwV1HIl37bKZMofoPypNZfY/"

@app.route("/")
def home():
    try:
        books = requests.get(BOOKS_URL).json()
    except:
        books = []
    return render_template("index.html", books=books)

if __name__ == "__main__":
    app.run(debug=True)