import os
import re
import hashlib
import json
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

UPSTASH_REDIS_REST_URL = os.environ.get(
    "UPSTASH_REDIS_REST_URL",
    ""
).rstrip("/")

UPSTASH_REDIS_REST_TOKEN = os.environ.get(
    "UPSTASH_REDIS_REST_TOKEN",
    ""
)


def normalize_keyword(keyword):
    if not isinstance(keyword, str):
        return None

    keyword = keyword.strip().lower()
    if not re.fullmatch(r"[a-z0-9_-]{12,64}", keyword):
        return None

    return keyword


def keyword_digest(keyword):
    return hashlib.sha256(keyword.encode("utf-8")).hexdigest()


def redis_command(*command):
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        raise RuntimeError("Upstash Redis is not configured.")

    response = requests.post(
        UPSTASH_REDIS_REST_URL,
        headers={
            "Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"
        },
        json=list(command),
        timeout=10
    )
    response.raise_for_status()
    result = response.json()
    if result.get("error"):
        raise RuntimeError(result["error"])

    return result.get("result")


def account_redis_key(keyword):
    return "ereader:account:" + keyword_digest(keyword)


def account_keyword_from_json():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        payload = {}

    keyword = normalize_keyword(payload.get("keyword"))
    if not keyword:
        return None, (jsonify({
            "success": False,
            "error": "Choose a private keyword using 12-64 letters, numbers, hyphens, or underscores."
        }), 400)

    return keyword, None


def storage_unavailable(error):
    print("Account storage error:", str(error))
    return jsonify({
        "success": False,
        "error": "Account storage is unavailable. Configure Upstash Redis in Vercel and try again."
    }), 503


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
            + "?type="
            + file_type
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


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# BOOKSHELF
# ============================================================

@app.route("/bookshelf")
def bookshelf():

    return render_template(
        "index.html"
    )


# ============================================================
# READER
# ============================================================

@app.route("/reader")
def reader():

    return render_template(
        "reader.html"
    )

@app.route("/setup")
def setup():
    return render_template(
        "setup.html"
    )


@app.route("/api/account", methods=["POST"])
def create_account():
    keyword, error = account_keyword_from_json()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    folder_url = payload.get("folderUrl", "")
    if not isinstance(folder_url, str):
        folder_url = ""
    folder_url = folder_url.strip()
    if not extract_folder_id(folder_url):
        return jsonify({
            "success": False,
            "error": "A valid Google Drive folder URL is required."
        }), 400

    reading_data = payload.get("readingData", {})
    history = payload.get("history", [])
    if (
        not isinstance(reading_data, dict)
        or not isinstance(history, list)
        or any(not isinstance(item, dict) for item in history)
    ):
        return jsonify({
            "success": False,
            "error": "Initial reading data is invalid."
        }), 400

    account_key = account_redis_key(keyword)
    try:
        created = redis_command(
            "HSETNX",
            account_key,
            "folderUrl",
            folder_url
        )
        if not created:
            return jsonify({
                "success": False,
                "error": "That keyword is already in use. Restore its library or choose another keyword."
            }), 409

        initial_fields = []
        for book_id, saved in reading_data.items():
            if isinstance(book_id, str) and re.fullmatch(
                r"[a-zA-Z0-9_-]{1,200}", book_id
            ) and isinstance(saved, dict):
                initial_fields.extend((
                    "reading:" + book_id,
                    json.dumps(saved)
                ))

        for item in history[:50]:
            book_id = item.get("id")
            if isinstance(book_id, str) and re.fullmatch(
                r"[a-zA-Z0-9_-]{1,200}", book_id
            ):
                initial_fields.extend((
                    "history:" + book_id,
                    json.dumps(item)
                ))

        if initial_fields:
            redis_command("HSET", account_key, *initial_fields)
    except Exception as error:
        return storage_unavailable(error)

    return jsonify({"success": True}), 201


@app.route("/api/account/session", methods=["POST"])
def restore_account():
    keyword, error = account_keyword_from_json()
    if error:
        return error

    try:
        values = redis_command(
            "HGETALL",
            account_redis_key(keyword)
        )
    except Exception as error:
        return storage_unavailable(error)

    if isinstance(values, dict):
        account = values
    else:
        account = dict(zip(values[::2], values[1::2])) if values else {}
    folder_url = account.get("folderUrl")
    if not folder_url:
        return jsonify({
            "success": False,
            "error": "No library was found for that keyword."
        }), 404

    reading_data = {}
    history = []
    for field, value in account.items():
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            continue

        if field.startswith("reading:"):
            reading_data[field[8:]] = parsed
        elif field.startswith("history:") and isinstance(parsed, dict):
            history.append(parsed)

    history.sort(
        key=lambda item: item.get("lastRead", item.get("openedAt", "")),
        reverse=True
    )
    return jsonify({
        "success": True,
        "folderUrl": folder_url,
        "readingData": reading_data,
        "history": history[:50]
    })


@app.route("/api/account/progress", methods=["PUT"])
def save_account_progress():
    keyword, error = account_keyword_from_json()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    book_id = str(payload.get("bookId", ""))
    reading_data = payload.get("readingData")
    history_entry = payload.get("historyEntry")
    if (
        not re.fullmatch(r"[a-zA-Z0-9_-]{1,200}", book_id)
        or not isinstance(reading_data, dict)
        or not isinstance(history_entry, dict)
    ):
        return jsonify({
            "success": False,
            "error": "Reading progress is invalid."
        }), 400

    account_key = account_redis_key(keyword)
    try:
        if not redis_command("HEXISTS", account_key, "folderUrl"):
            return jsonify({
                "success": False,
                "error": "No library was found for that keyword."
            }), 404

        history_entry["id"] = book_id
        redis_command(
            "HSET",
            account_key,
            "reading:" + book_id,
            json.dumps(reading_data),
            "history:" + book_id,
            json.dumps(history_entry)
        )
    except Exception as error:
        return storage_unavailable(error)

    return jsonify({"success": True})


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

        request_headers = {}
        range_header = request.headers.get("Range")

        if range_header:
            request_headers["Range"] = range_header

        response = requests.get(

            google_url,

            params=params,

            headers=request_headers,

            timeout=60,

            stream=True

        )


        if response.status_code not in (200, 206):

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

        elif request.args.get("type") == "epub":
            content_type = "application/epub+zip"


        # ----------------------------------------------------
        # Return file to browser
        # ----------------------------------------------------

        response_headers = {

            "Cache-Control":
                "public, max-age=3600",

            "Content-Disposition":
                "inline"

        }

        for header_name in (
            "Content-Length",
            "Content-Range",
            "Accept-Ranges"
        ):

            header_value = response.headers.get(
                header_name
            )

            if header_value:
                response_headers[header_name] = header_value

        def generate_file_stream():
            iter_content = getattr(response, "iter_content", None)
            if callable(iter_content):
                try:
                    chunks = iter_content(chunk_size=65536)
                except TypeError:
                    chunks = None

                if chunks is not None and hasattr(chunks, "__iter__"):
                    for chunk in chunks:
                        if chunk:
                            yield chunk
                    return

            content = getattr(response, "content", None)
            if content:
                yield content

        return Response(

            generate_file_stream(),

            status=response.status_code,

            content_type=content_type,

            headers=response_headers

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
