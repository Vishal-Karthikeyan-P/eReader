import os
import re
import requests

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    Response
)


# ============================================================
# Flask
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

app = Flask(
    __name__,
    template_folder=os.path.join(
        BASE_DIR,
        "templates"
    )
)


# ============================================================
# Google Drive configuration
# ============================================================

DRIVE_API_KEY = os.environ.get(
    "DRIVE_API_KEY",
    ""
)

DRIVE_API_URL = (
    "https://www.googleapis.com/drive/v3/files"
)


# ============================================================
# Extract Google Drive folder ID
# ============================================================

def extract_folder_id(url):

    if not url:
        return None

    url = url.strip()

    # If the user directly entered an ID
    if re.fullmatch(
        r"[a-zA-Z0-9_-]{10,}",
        url
    ):
        return url

    # Normal folder URL
    match = re.search(
        r"/folders/([a-zA-Z0-9_-]+)",
        url
    )

    if match:
        return match.group(1)

    return None


# ============================================================
# Get files from Google Drive
# ============================================================

def get_books_from_drive(folder_id):

    if not DRIVE_API_KEY:

        raise Exception(
            "DRIVE_API_KEY is not configured."
        )

    params = {

        "q": (
            f"'{folder_id}' in parents "
            "and trashed = false "
            "and ("
            "mimeType = 'application/pdf' "
            "or "
            "mimeType = 'application/epub+zip' "
            "or "
            "name contains '.epub'"
            ")"
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
            f"Google Drive API error "
            f"{response.status_code}: "
            f"{response.text}"
        )


    data = response.json()

    books = []


    for file in data.get(
        "files",
        []
    ):

        file_id = file.get(
            "id"
        )

        name = file.get(
            "name",
            ""
        )

        mime_type = file.get(
            "mimeType",
            ""
        )


        # --------------------------------------------
        # Determine type
        # --------------------------------------------

        if (
            mime_type == "application/pdf"
            or
            name.lower().endswith(".pdf")
        ):

            file_type = "pdf"


        elif (
            mime_type == "application/epub+zip"
            or
            name.lower().endswith(".epub")
        ):

            file_type = "epub"


        else:

            continue


        # --------------------------------------------
        # Google Drive viewer URL
        # --------------------------------------------

        view_url = file.get(
            "webViewLink"
        )


        if not view_url:

            view_url = (
                "https://drive.google.com/file/d/"
                + file_id
                + "/view"
            )


        # --------------------------------------------
        # IMPORTANT
        #
        # We DON'T expose the Google API key here.
        #
        # The browser will request:
        #
        # /api/file/<file_id>
        #
        # --------------------------------------------

        proxy_url = (
            "/api/file/"
            + file_id
        )


        books.append({

            "id":
                file_id,

            "title":
                os.path.splitext(
                    name
                )[0],

            "name":
                name,

            "type":
                file_type,

            "link":
                view_url,

            "download_url":
                proxy_url,

            "thumbnail":
                file.get(
                    "thumbnailLink"
                ),

            "modifiedTime":
                file.get(
                    "modifiedTime"
                ),

            "size":
                file.get(
                    "size"
                )

        })


    return books


# Home / Landing Page
@app.route("/")
def home():
    return render_template("index.html")


# Setup Page
@app.route("/setup")
def setup():
    return render_template("setup.html")


# Bookshelf Page
@app.route("/bookshelf")
def bookshelf():
    return render_template("bookshelf.html")


# Reader Page
@app.route("/reader")
def reader():
    return render_template("reader.html")
# ============================================================
# BOOK API
# ============================================================

@app.route("/api/books")
def books_api():

    folder_url = request.args.get(
        "folder"
    )


    if not folder_url:

        return jsonify({

            "success": False,

            "error":
                "Google Drive folder URL is required.",

            "books": []

        }), 400


    folder_id = extract_folder_id(
        folder_url
    )


    if not folder_id:

        return jsonify({

            "success": False,

            "error":
                "Invalid Google Drive folder URL.",

            "books": []

        }), 400


    try:

        books = get_books_from_drive(
            folder_id
        )


        return jsonify({

            "success": True,

            "books": books,

            "count":
                len(books)

        })


    except Exception as e:

        print(
            "Google Drive error:",
            str(e)
        )


        return jsonify({

            "success": False,

            "error":
                str(e),

            "books": []

        }), 500


# ============================================================
# FILE PROXY
#
# Browser:
#
# /api/file/FILE_ID
#
# Server:
#
# Google Drive API
#
# This keeps the API key on the server.
# ============================================================

@app.route(
    "/api/file/<file_id>"
)
def file_proxy(file_id):

    if not DRIVE_API_KEY:

        return jsonify({

            "error":
                "DRIVE_API_KEY is not configured."

        }), 500


    # Basic validation
    if not re.fullmatch(
        r"[a-zA-Z0-9_-]+",
        file_id
    ):

        return jsonify({

            "error":
                "Invalid file ID."

        }), 400


    try:

        google_url = (
            f"https://www.googleapis.com/drive/v3/files/"
            f"{file_id}"
        )


        params = {

            "alt":
                "media",

            "key":
                DRIVE_API_KEY

        }


        # ----------------------------------------------------
        # Download file from Google
        # ----------------------------------------------------

        response = requests.get(

            google_url,

            params=params,

            timeout=60,

            stream=True

        )


        if response.status_code != 200:

            print(
                "Google Drive file error:",
                response.status_code,
                response.text
            )


            return Response(

                response.text,

                status=response.status_code,

                content_type=(
                    response.headers.get(
                        "Content-Type",
                        "text/plain"
                    )
                )

            )


        # ----------------------------------------------------
        # Determine content type
        # ----------------------------------------------------

        content_type = (
            response.headers.get(
                "Content-Type",
                "application/octet-stream"
            )
        )


        # Google may occasionally return a generic type.
        # PDF.js is happier with application/pdf.

        if (
            "application/pdf"
            in content_type.lower()
        ):

            content_type = (
                "application/pdf"
            )


        # ----------------------------------------------------
        # Return file to browser
        # ----------------------------------------------------

        return Response(

            response.content,

            status=200,

            content_type=content_type,

            headers={

                "Cache-Control":
                    "public, max-age=3600",

                "Content-Disposition":
                    "inline"

            }

        )


    except requests.RequestException as e:

        print(
            "File proxy error:",
            str(e)
        )


        return jsonify({

            "error":
                "Unable to download file from Google Drive.",

            "details":
                str(e)

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/api/health"
)
def health():

    return jsonify({

        "status":
            "ok"

    })


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
