from flask import Flask, render_template, request, jsonify
import requests
import re
import os

# --------------------------------------------------
# Flask application
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates")
)


# --------------------------------------------------
# Google Drive API
# --------------------------------------------------

DRIVE_API_KEY = os.environ.get("DRIVE_API_KEY", "")

DRIVE_API_URL = "https://www.googleapis.com/drive/v3/files"


# --------------------------------------------------
# Helper: extract Google Drive folder ID
# --------------------------------------------------

def extract_folder_id(url):
    """
    Accepts:
        https://drive.google.com/drive/folders/FOLDER_ID
        https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing

    Also accepts the folder ID directly.
    """

    if not url:
        return None

    url = url.strip()

    # Direct folder ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", url):
        return url

    # /folders/FOLDER_ID
    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)

    if match:
        return match.group(1)

    return None


# --------------------------------------------------
# Google Drive: get books
# --------------------------------------------------

def get_books_from_drive(folder_id):

    if not DRIVE_API_KEY:
        raise Exception("DRIVE_API_KEY is not configured on Vercel.")

    params = {
        "q": (
            f"'{folder_id}' in parents "
            "and trashed = false "
            "and (mimeType = 'application/pdf' "
            "or mimeType = 'application/epub+zip' "
            "or name contains '.epub')"
        ),
        "key": DRIVE_API_KEY,
        "fields": (
            "files("
            "id,"
            "name,"
            "mimeType,"
            "modifiedTime,"
            "size,"
            "webViewLink,"
            "thumbnailLink"
            ")"
        ),
        "pageSize": 1000
    }

    response = requests.get(
        DRIVE_API_URL,
        params=params,
        timeout=20
    )

    if response.status_code != 200:
        raise Exception(
            f"Google Drive API error {response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    books = []

    for file in data.get("files", []):

        name = file.get("name", "")
        mime_type = file.get("mimeType", "")

        # Determine extension
        if (
            mime_type == "application/pdf"
            or name.lower().endswith(".pdf")
        ):
            file_type = "pdf"

        elif (
            mime_type == "application/epub+zip"
            or name.lower().endswith(".epub")
        ):
            file_type = "epub"

        else:
            continue

        file_id = file.get("id")

        # Direct Google Drive download URL
        download_url = (
            f"https://drive.google.com/uc"
            f"?export=download&id={file_id}"
        )

        # Browser/view URL
        view_url = file.get("webViewLink")

        if not view_url:
            view_url = (
                f"https://drive.google.com/file/d/"
                f"{file_id}/view"
            )

        books.append({
            "id": file_id,
            "title": os.path.splitext(name)[0],
            "name": name,
            "type": file_type,
            "link": view_url,
            "download_url": download_url,
            "thumbnail": file.get("thumbnailLink"),
            "modifiedTime": file.get("modifiedTime"),
            "size": file.get("size")
        })

    return books


# --------------------------------------------------
# Home
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# Bookshelf
# --------------------------------------------------

@app.route("/bookshelf")
def bookshelf():
    return render_template("bookshelf.html")


# --------------------------------------------------
# Reader
# --------------------------------------------------

@app.route("/reader")
def reader():
    return render_template("reader.html")


# --------------------------------------------------
# API: fetch books from Drive
# --------------------------------------------------

@app.route("/api/books")
def books_api():

    folder_url = request.args.get("folder")

    if not folder_url:
        return jsonify({
            "success": False,
            "error": "Google Drive folder URL is required.",
            "books": []
        }), 400

    folder_id = extract_folder_id(folder_url)

    if not folder_id:
        return jsonify({
            "success": False,
            "error": "Invalid Google Drive folder URL.",
            "books": []
        }), 400

    try:

        books = get_books_from_drive(folder_id)

        return jsonify({
            "success": True,
            "books": books,
            "count": len(books)
        })

    except Exception as e:

        print("Drive error:", str(e))

        return jsonify({
            "success": False,
            "error": str(e),
            "books": []
        }), 500


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.route("/api/health")
def health():

    return jsonify({
        "status": "ok"
    })


# --------------------------------------------------
# IMPORTANT:
# Do NOT put the Flask app inside this block.
#
# Vercel needs to find:
#
#     app = Flask(...)
#
# at module level.
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
