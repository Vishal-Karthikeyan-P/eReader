from flask import Flask, render_template, jsonify, request
import requests
import re
import os


app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)


# ============================================================
# GOOGLE DRIVE CONFIGURATION
# ============================================================

DRIVE_API_KEY = os.getenv("GOOGLE_DRIVE_API_KEY")

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

    print("Received folder value:")
    print(value)

    # --------------------------------------------------------
    # Standard Google Drive folder URL
    #
    # https://drive.google.com/drive/folders/FOLDER_ID
    # --------------------------------------------------------

    match = re.search(
        r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)",
        value
    )

    if match:

        folder_id = match.group(1)

        print(
            "Extracted folder ID:",
            folder_id
        )

        return folder_id


    # --------------------------------------------------------
    # Also support:
    #
    # https://drive.google.com/open?id=FOLDER_ID
    # --------------------------------------------------------

    match = re.search(
        r"[?&]id=([a-zA-Z0-9_-]+)",
        value
    )

    if match:

        folder_id = match.group(1)

        print(
            "Extracted folder ID:",
            folder_id
        )

        return folder_id


    # --------------------------------------------------------
    # If user supplied only the ID
    # --------------------------------------------------------

    if re.fullmatch(
        r"[a-zA-Z0-9_-]+",
        value
    ):

        print(
            "Input itself is folder ID:",
            value
        )

        return value


    print(
        "Could not extract folder ID"
    )

    return None


# ============================================================
# GET FILES FROM GOOGLE DRIVE
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


        print()
        print(
            "=========================================="
        )

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
            timeout=30
        )


        print(
            "HTTP status:",
            response.status_code
        )


        print(
            "Response:"
        )

        print(
            response.text
        )


        if response.status_code != 200:

            try:

                error_data = (
                    response.json()
                )

            except Exception:

                error_data = (
                    response.text
                )


            raise RuntimeError(
                "Google Drive API rejected "
                f"the request: {error_data}"
            )


        data = response.json()


        files = data.get(
            "files",
            []
        )


        print(
            "Files returned:",
            len(files)
        )


        for file in files:

            print(
                " -",
                file.get("name"),
                "|",
                file.get("mimeType"),
                "|",
                file.get("id")
            )


        all_files.extend(
            files
        )


        page_token = data.get(
            "nextPageToken"
        )


        if not page_token:

            break


    return all_files


# ============================================================
# CREATE BOOK LIST
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


        # ====================================================
        # PDF
        # ====================================================

        is_pdf = (
            mime_type == "application/pdf"
            or name.lower().endswith(".pdf")
        )


        # ====================================================
        # EPUB
        # ====================================================

        is_epub = (
            mime_type
            in [
                "application/epub+zip",
                "application/epub",
            ]
            or name.lower().endswith(".epub")
        )


        # Ignore everything else
        #
        # This automatically ignores:
        # books.json
        # folders
        # images
        # documents
        # etc.
        #

        if not is_pdf and not is_epub:

            print(
                "Ignoring:",
                name,
                "|",
                mime_type
            )

            continue


        if is_pdf:

            book_type = "pdf"

        else:

            book_type = "epub"


        title = name


        if "." in title:

            title = title.rsplit(
                ".",
                1
            )[0]


        # Direct Google Drive download URL

        download_url = (
            "https://drive.google.com/uc"
            f"?export=download&id={file_id}"
        )


        book = {

            "id":
                file_id,

            "title":
                title,

            "filename":
                name,

            "type":
                book_type,

            "link":
                download_url,

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

        }


        books.append(
            book
        )


    books.sort(
        key=lambda book:
        book["title"].lower()
    )


    print()
    print(
        "=========================================="
    )

    print(
        "FINAL BOOK COUNT:",
        len(books)
    )


    for book in books:

        print(
            "BOOK:",
            book["title"],
            "|",
            book["type"]
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


    print()
    print(
        "=========================================="
    )

    print(
        "LIBRARY REQUEST"
    )

    print(
        "Folder URL:",
        folder_url
    )


    if not folder_url:

        return jsonify({

            "success": False,

            "error":
                "No Google Drive folder was supplied."

        }), 400


    folder_id = extract_folder_id(
        folder_url
    )


    if not folder_id:

        return jsonify({

            "success": False,

            "error":
                "Could not extract a valid Google Drive folder ID.",

            "received":
                folder_url

        }), 400


    try:

        files = get_drive_files(
            folder_id
        )


        books = create_books(
            files
        )


        return jsonify({

            "success":
                True,

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
            str(error)
        )


        return jsonify({

            "success":
                False,

            "error":
                str(error),

            "folderId":
                folder_id

        }), 500


# ============================================================
# HEALTH CHECK
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
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
