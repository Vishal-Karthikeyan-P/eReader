from flask import Flask, render_template, jsonify, request
import requests
import re
import os

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

DRIVE_API_KEY = os.getenv("GOOGLE_DRIVE_API_KEY")


def extract_folder_id(url):
    """
    Extract Google Drive folder ID from URLs such as:

    https://drive.google.com/drive/folders/FOLDER_ID
    https://drive.google.com/drive/u/0/folders/FOLDER_ID
    """

    if not url:
        return None

    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)

    if match:
        return match.group(1)

    # Also allow a raw folder ID
    if re.match(r"^[a-zA-Z0-9_-]+$", url):
        return url

    return None


def get_drive_files(folder_id):
    """
    Retrieve files from a public Google Drive folder.
    """

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
                "files(id,name,mimeType,size,modifiedTime,"
                "webViewLink,thumbnailLink)"
            ),
            "pageSize": 1000,
            "key": DRIVE_API_KEY
        }

        if page_token:
            params["pageToken"] = page_token

        response = requests.get(
            DRIVE_API_URL,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        files.extend(data.get("files", []))

        page_token = data.get("nextPageToken")

        if not page_token:
            break

    return files


def create_books_json(files):
    """
    Convert Google Drive files into the structure
    used by the bookshelf.
    """

    books = []

    supported_extensions = (
        ".pdf",
        ".epub"
    )

    for file in files:

        name = file.get("name", "")
        lower_name = name.lower()

        if not lower_name.endswith(supported_extensions):
            continue

        file_id = file["id"]

        extension = lower_name.rsplit(".", 1)[-1]

        # Direct download URL
        download_url = (
            "https://drive.google.com/uc"
            f"?export=download&id={file_id}"
        )

        book = {
            "id": file_id,
            "title": name.rsplit(".", 1)[0],
            "filename": name,
            "type": extension,
            "link": download_url,
            "driveLink": file.get("webViewLink", ""),
            "thumbnail": file.get("thumbnailLink", ""),
            "modifiedTime": file.get("modifiedTime", ""),
            "size": file.get("size", "")
        }

        books.append(book)

    books.sort(
        key=lambda x: x["title"].lower()
    )

    return books


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/setup")
def setup():
    return render_template("setup.html")


@app.route("/reader")
def reader():
    return render_template("reader.html")


@app.route("/api/library")
def library():

    folder_url = request.args.get("folder")

    if not folder_url:
        return jsonify({
            "success": False,
            "error": "Drive folder URL is required"
        }), 400

    folder_id = extract_folder_id(folder_url)

    if not folder_id:
        return jsonify({
            "success": False,
            "error": "Invalid Google Drive folder URL"
        }), 400

    try:

        files = get_drive_files(folder_id)

        books = create_books_json(files)

        return jsonify({
            "success": True,
            "folderId": folder_id,
            "books": books,
            "count": len(books)
        })

    except requests.exceptions.RequestException as e:

        return jsonify({
            "success": False,
            "error": "Unable to access Google Drive",
            "details": str(e)
        }), 500

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/books.json")
def books_json():

    folder_url = request.args.get("folder")

    if not folder_url:
        return jsonify({
            "success": False,
            "error": "Folder URL required"
        }), 400

    folder_id = extract_folder_id(folder_url)

    if not folder_id:
        return jsonify({
            "success": False,
            "error": "Invalid folder URL"
        }), 400

    try:

        files = get_drive_files(folder_id)

        books = create_books_json(files)

        return jsonify(books)

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
