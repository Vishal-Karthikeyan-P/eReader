from flask import Flask, render_template, jsonify, request
import requests
import re
import os


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)


# ============================================================
# GOOGLE DRIVE CONFIGURATION
# ============================================================

# This comes from Vercel Environment Variables.
#
# Vercel:
# Project
#   -> Settings
#   -> Environment Variables
#
# Name:
# GOOGLE_DRIVE_API_KEY
#
DRIVE_API_KEY = os.getenv(
    "GOOGLE_DRIVE_API_KEY"
)

DRIVE_API_URL = (
    "https://www.googleapis.com/drive/v3/files"
)


# ============================================================
# EXTRACT DRIVE FOLDER ID
# ============================================================

def extract_folder_id(url):

    if not url:
        return None

    url = url.strip()

    # Standard Drive folder URL
    match = re.search(
        r"/folders/([a-zA-Z0-9_-]+)",
        url
    )

    if match:
        return match.group(1)

    # Allow just the folder ID
    if re.fullmatch(
        r"[a-zA-Z0-9_-]+",
        url
    ):
        return url

    return None


# ============================================================
# GET FILES FROM GOOGLE DRIVE
# ============================================================

def get_drive_files(folder_id):

    if not DRIVE_API_KEY:

        raise RuntimeError(
            "GOOGLE_DRIVE_API_KEY is not configured in Vercel."
        )

    files = []

    page_token = None

    while True:

        params = {

            "q": (
                f"'{folder_id}' in parents "
                "and trashed = false"
            ),

            "fields": (
                "nextPageToken,"
                "files("
                "id,"
                "name,"
                "mimeType,"
                "size,"
                "modifiedTime,"
                "webViewLink,"
                "thumbnailLink"
                ")"
            ),

            "pageSize": 1000,

            "key": DRIVE_API_KEY
        }

        if page_token:
            params["pageToken"] = page_token

        print(
            "Google Drive request"
        )

        print(
            "Folder ID:",
            folder_id
        )

        response = requests.get(
            DRIVE_API_URL,
            params=params,
            timeout=20
        )

        print(
            "Google Drive status:",
            response.status_code
        )

        print(
            "Google Drive response:",
            response.text
        )

        if not response.ok:

            try:
                error_data = response.json()
            except Exception:
                error_data = response.text

            raise RuntimeError(
                "Google Drive API error "
                f"({response.status_code}): "
                f"{error_data}"
            )

        data = response.json()

        returned_files = data.get(
            "files",
            []
        )

        print(
            "Files returned:",
            len(returned_files)
        )

        for file in returned_files:

            print(
                "FILE:",
                file.get("name"),
                "| MIME:",
                file.get("mimeType")
            )

        files.extend(
            returned_files
        )

        page_token = data.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return files


# ============================================================
# CONVERT DRIVE FILES TO BOOKS
# ============================================================

def create_books_json(files):

    books = []

    for file in files:

        name = file.get(
            "name",
            ""
        )

        lower_name = name.lower()

        # Ignore books.json and every other file.
        if lower_name.endswith(".pdf"):

            book_type = "pdf"

        elif lower_name.endswith(".epub"):

            book_type = "epub"

        else:

            continue

        file_id = file.get(
            "id"
        )

        if not file_id:
            continue

        download_url = (
            "https://drive.google.com/uc"
            f"?export=download&id={file_id}"
        )

        book = {

            "id": file_id,

            "title": name.rsplit(
                ".",
                1
            )[0],

            "filename": name,

            "type": book_type,

            "link": download_url,

            "driveLink": file.get(
                "webViewLink",
                ""
            ),

            "thumbnail": file.get(
                "thumbnailLink",
                ""
            ),

            "modifiedTime": file.get(
                "modifiedTime",
                ""
            ),

            "size": file.get(
                "size",
                ""
            )

        }

        books.append(book)

    books.sort(
        key=lambda book:
        book["title"].lower()
    )

    print(
        "Books created:",
        len(books)
    )

    return books


# ============================================================
# HOME / BOOKSHELF
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# SETUP PAGE
# ============================================================

@app.route("/setup")
def setup():

    return render_template(
        "setup.html"
    )


# ============================================================
# READER PAGE
# ============================================================

@app.route("/reader")
def reader():

    return render_template(
        "reader.html"
    )


# ============================================================
# LIBRARY API
# ============================================================

@app.route("/api/library")
def library():

    folder_url = request.args.get(
        "folder"
    )

    if not folder_url:

        return jsonify({

            "success": False,

            "error":
                "Google Drive folder URL is required."

        }), 400

    folder_id = extract_folder_id(
        folder_url
    )

    if not folder_id:

        return jsonify({

            "success": False,

            "error":
                "Invalid Google Drive folder URL.",

            "received":
                folder_url

        }), 400

    try:

        files = get_drive_files(
            folder_id
        )

        books = create_books_json(
            files
        )

        return jsonify({

            "success": True,

            "folderId":
                folder_id,

            "count":
                len(books),

            "books":
                books

        })

    except Exception as e:

        print(
            "LIBRARY ERROR:",
            str(e)
        )

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500


# ============================================================
# BOOKS.JSON ENDPOINT
# ============================================================

@app.route("/api/books.json")
def books_json():

    folder_url = request.args.get(
        "folder"
    )

    if not folder_url:

        return jsonify({

            "success": False,

            "error":
                "Google Drive folder URL is required."

        }), 400

    folder_id = extract_folder_id(
        folder_url
    )

    if not folder_id:

        return jsonify({

            "success": False,

            "error":
                "Invalid Google Drive folder URL."

        }), 400

    try:

        files = get_drive_files(
            folder_id
        )

        books = create_books_json(
            files
        )

        return jsonify({

            "success": True,

            "count":
                len(books),

            "books":
                books

        })

    except Exception as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({

        "status":
            "ok",

        "drive_api_key_configured":
            bool(DRIVE_API_KEY)

    })


# ============================================================
# RUN LOCALLY
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
