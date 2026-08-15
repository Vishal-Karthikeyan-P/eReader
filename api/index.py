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

# This value comes from Vercel:
#
# Vercel
#   → Project
#   → Settings
#   → Environment Variables
#   → GOOGLE_DRIVE_API_KEY
#
DRIVE_API_KEY = os.getenv("GOOGLE_DRIVE_API_KEY")


# Google Drive API endpoint
DRIVE_API_URL = "https://www.googleapis.com/drive/v3/files"


# ============================================================
# FOLDER ID EXTRACTION
# ============================================================

def extract_folder_id(url):
    """
    Extract the Google Drive folder ID from a folder URL.

    Example:

    https://drive.google.com/drive/folders/ABC123XYZ

    returns:

    ABC123XYZ
    """

    if not url:
        return None

    url = url.strip()

    # Standard Google Drive folder URL
    match = re.search(
        r"/folders/([a-zA-Z0-9_-]+)",
        url
    )

    if match:
        return match.group(1)

    # Also allow the user to enter only the folder ID
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
    """
    Get all files directly inside the selected Google Drive folder.

    This application does NOT search subfolders.
    """

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

        print("----------------------------------------")
        print("Google Drive request")
        print("Folder ID:", folder_id)
        print("----------------------------------------")

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

        # If Google rejects the request
        if not response.ok:

            try:
                google_error = response.json()
            except Exception:
                google_error = response.text

            raise RuntimeError(
                f"Google Drive API error "
                f"({response.status_code}): "
                f"{google_error}"
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

        files.extend(returned_files)

        page_token = data.get(
            "nextPageToken"
        )

        if not page_token:
            break

    print("----------------------------------------")
    print(
        "TOTAL FILES:",
        len(files)
    )
    print("----------------------------------------")

    return files


# ============================================================
# CREATE BOOK LIST
# ============================================================

def create_books_json(files):
    """
    Convert Google Drive files into the structure
    used by the frontend.

    Only PDF and EPUB files are included.
    """

    books = []

    for file in files:

        name = file.get(
            "name",
            ""
        )

        lower_name = name.lower()

        # ----------------------------------------------------
        # PDF
        # ----------------------------------------------------

        if lower_name.endswith(".pdf"):

            book_type = "pdf"

        # ----------------------------------------------------
        # EPUB
        # ----------------------------------------------------

        elif lower_name.endswith(".epub"):

            book_type = "epub"

        # ----------------------------------------------------
        # Ignore everything else
        # ----------------------------------------------------

        else:

            continue

        file_id = file.get(
            "id"
        )

        if not file_id:
            continue

        # Direct Google Drive download URL
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

    # Sort alphabetically
    books.sort(
        key=lambda book:
        book["title"].lower()
    )

    print("----------------------------------------")
    print(
        "BOOKS CREATED:",
        len(books)
    )
    print("----------------------------------------")

    for book in books:

        print(
            book["title"],
            "|",
            book["type"]
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

    # --------------------------------------------------------
    # No folder supplied
    # --------------------------------------------------------

    if not folder_url:

        return jsonify({

            "success": False,

            "error":
                "Google Drive folder URL is required."

        }), 400

    # --------------------------------------------------------
    # Extract folder ID
    # --------------------------------------------------------

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

    print("----------------------------------------")
    print(
        "LIBRARY REQUEST"
    )
    print(
        "Folder URL:",
        folder_url
    )
    print(
        "Folder ID:",
        folder_id
    )
    print("----------------------------------------")

    # --------------------------------------------------------
    # Get files
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Google/API error
    # --------------------------------------------------------

    except RuntimeError as e:

        print(
            "DRIVE ERROR:",
            str(e)
        )

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500

    # --------------------------------------------------------
    # Requests/network error
    # --------------------------------------------------------

    except requests.exceptions.RequestException as e:

        print(
            "NETWORK ERROR:",
            str(e)
        )

        return jsonify({

            "success": False,

            "error":
                "Unable to connect to Google Drive API.",

            "details":
                str(e)

        }), 500

    # --------------------------------------------------------
    # Unexpected error
    # --------------------------------------------------------

    except Exception as e:

        print(
            "UNEXPECTED ERROR:",
            str(e)
        )

        return jsonify({

            "success": False,

            "error":
                "Unexpected server error.",

            "details":
                str(e)

        }), 500


# ============================================================
# BOOKS.JSON API
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

        print(
            "BOOKS.JSON ERROR:",
            str(e)
        )

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500


# ============================================================
# API HEALTH CHECK
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
