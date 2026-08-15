from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    Response,
    stream_with_context
)

import requests
import re
import os


# ============================================================
# FLASK
# ============================================================

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)


# ============================================================
# GOOGLE DRIVE
# ============================================================

DRIVE_API_KEY = os.getenv(
    "GOOGLE_DRIVE_API_KEY"
)

DRIVE_API_URL = (
    "https://www.googleapis.com/drive/v3/files"
)


# ============================================================
# EXTRACT FOLDER ID
# ============================================================

def extract_folder_id(value):

    if not value:
        return None

    value = value.strip()

    # Normal folder URL
    match = re.search(
        r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)",
        value
    )

    if match:
        return match.group(1)

    # Open?id=...
    match = re.search(
        r"[?&]id=([a-zA-Z0-9_-]+)",
        value
    )

    if match:
        return match.group(1)

    # Raw folder ID
    if re.fullmatch(
        r"[a-zA-Z0-9_-]+",
        value
    ):
        return value

    return None


# ============================================================
# GET DRIVE FILES
# ============================================================

def get_drive_files(folder_id):

    if not DRIVE_API_KEY:

        raise RuntimeError(
            "GOOGLE_DRIVE_API_KEY is not configured."
        )

    all_files = []

    page_token = None

    while True:

        params = {

            "q":
                f"'{folder_id}' in parents "
                "and trashed = false",

            "key":
                DRIVE_API_KEY,

            "pageSize":
                1000,

            "fields":
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
        }

        if page_token:
            params["pageToken"] = page_token

        response = requests.get(
            DRIVE_API_URL,
            params=params,
            timeout=30
        )

        print(
            "Drive status:",
            response.status_code
        )

        print(
            "Drive response:",
            response.text
        )

        if not response.ok:

            try:
                error = response.json()
            except Exception:
                error = response.text

            raise RuntimeError(
                f"Google Drive API error: {error}"
            )

        data = response.json()

        files = data.get(
            "files",
            []
        )

        all_files.extend(files)

        page_token = data.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return all_files


# ============================================================
# CONVERT DRIVE FILES TO BOOKS
# ============================================================

def create_books(files):

    books = []

    for file in files:

        name = file.get(
            "name",
            ""
        )

        file_id = file.get(
            "id"
        )

        mime_type = file.get(
            "mimeType",
            ""
        )

        if not file_id:
            continue

        # PDF
        is_pdf = (
            mime_type == "application/pdf"
            or name.lower().endswith(".pdf")
        )

        # EPUB
        is_epub = (
            mime_type in [
                "application/epub+zip",
                "application/epub"
            ]
            or name.lower().endswith(".epub")
        )

        # Ignore books.json, folders, images, etc.
        if not is_pdf and not is_epub:
            continue

        book_type = (
            "pdf"
            if is_pdf
            else "epub"
        )

        title = name

        if "." in title:

            title = title.rsplit(
                ".",
                1
            )[0]

        books.append({

            "id":
                file_id,

            "title":
                title,

            "filename":
                name,

            "type":
                book_type,

            # IMPORTANT:
            # Browser uses our proxy instead of
            # accessing Drive directly.
            "link":
                f"/api/book/{file_id}",

            "driveLink":
                file.get(
                    "webViewLink",
                    ""
                ),

            "thumbnail":
                file.get(
                    "thumbnailLink",
                    ""
                ),

            "modifiedTime":
                file.get(
                    "modifiedTime",
                    ""
                ),

            "size":
                file.get(
                    "size",
                    ""
                )

        })

    books.sort(
        key=lambda x:
        x["title"].lower()
    )

    print(
        "Books found:",
        len(books)
    )

    return books


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# SETUP
# ============================================================

@app.route("/setup")
def setup():

    return render_template(
        "setup.html"
    )


# ============================================================
# READER
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
        "folder",
        ""
    )

    if not folder_url:

        return jsonify({

            "success": False,

            "error":
                "Google Drive folder is required."

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

        books = create_books(
            files
        )

        return jsonify({

            "success": True,

            "folderId":
                folder_id,

            "filesFound":
                len(files),

            "count":
                len(books),

            "books":
                books

        })

    except Exception as error:

        print(
            "LIBRARY ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "error":
                str(error)

        }), 500


# ============================================================
# BOOK PROXY
#
# Browser:
#
# /api/book/FILE_ID
#
# Flask:
#
#        ↓
#
# Google Drive
#
# This prevents the browser from needing the API key.
# ============================================================

@app.route("/api/book/<file_id>")
def book_proxy(file_id):

    if not DRIVE_API_KEY:

        return jsonify({

            "error":
                "Google Drive API key is not configured."

        }), 500

    # Basic validation of Google Drive IDs
    if not re.fullmatch(
        r"[a-zA-Z0-9_-]+",
        file_id
    ):

        return jsonify({

            "error":
                "Invalid file ID."

        }), 400


    url = (
        f"{DRIVE_API_URL}/"
        f"{file_id}"
    )


    params = {

        "alt":
            "media",

        "key":
            DRIVE_API_KEY

    }


    try:

        drive_response = requests.get(

            url,

            params=params,

            stream=True,

            timeout=60

        )


        if not drive_response.ok:

            try:

                error_data =
                    drive_response.json()

            except Exception:

                error_data =
                    drive_response.text


            return jsonify({

                "error":
                    "Unable to retrieve book from Google Drive.",

                "details":
                    error_data

            }), drive_response.status_code


        content_type = (
            drive_response.headers.get(
                "Content-Type",
                "application/octet-stream"
            )
        )


        content_length = (
            drive_response.headers.get(
                "Content-Length"
            )
        )


        def generate():

            try:

                for chunk in drive_response.iter_content(
                    chunk_size=1024 * 1024
                ):

                    if chunk:

                        yield chunk

            finally:

                drive_response.close()


        headers = {

            "Content-Type":
                content_type,

            "Content-Disposition":
                "inline",

            "Cache-Control":
                "public, max-age=3600",

            "Access-Control-Allow-Origin":
                "*"

        }


        if content_length:

            headers["Content-Length"] = (
                content_length
            )


        return Response(

            stream_with_context(
                generate()
            ),

            status=200,

            headers=headers

        )


    except Exception as error:

        print(
            "BOOK PROXY ERROR:",
            error
        )

        return jsonify({

            "error":
                str(error)

        }), 500


# ============================================================
# HEALTH
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({

        "status":
            "ok",

        "apiKeyConfigured":
            bool(DRIVE_API_KEY)

    })


# ============================================================
# LOCAL
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
