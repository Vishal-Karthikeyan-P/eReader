from flask import Flask, render_template, request, Response, abort
import requests
import os
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR
)


# ---------------------------------------------------------
# Google Drive JSON
# ---------------------------------------------------------

BOOKS_URL = (
    "https://drive.google.com/uc"
    "?export=download"
    "&id=1GwKEkGCxFPwV1HIl37bKZMofoPypNZfY"
)


# ---------------------------------------------------------
# Home
# ---------------------------------------------------------

@app.route("/")
def home():

    try:
        response = requests.get(
            BOOKS_URL,
            timeout=15
        )

        response.raise_for_status()

        books = response.json()

    except Exception as e:

        print("ERROR LOADING BOOKS:", str(e))

        books = []

    return render_template(
        "index.html",
        books=books
    )


# ---------------------------------------------------------
# Reader
# ---------------------------------------------------------

@app.route("/reader")
def reader():

    title = request.args.get(
        "title",
        "Book Reader"
    )

    link = request.args.get(
        "link",
        ""
    )

    if not link:
        abort(400, "Book link is missing.")

    return render_template(
        "reader.html",
        title=title,
        link=link
    )


# ---------------------------------------------------------
# Validate Google Drive URLs
# ---------------------------------------------------------

def is_allowed_book_url(url):

    try:

        parsed = urlparse(url)

        hostname = (
            parsed.hostname or ""
        ).lower()

        allowed_hosts = (
            "drive.google.com",
            "docs.google.com",
            "drive.usercontent.google.com",
            "googleusercontent.com"
        )

        return (
            parsed.scheme == "https"
            and any(
                hostname == host
                or hostname.endswith("." + host)
                for host in allowed_hosts
            )
        )

    except Exception:

        return False


# ---------------------------------------------------------
# Book proxy
#
# This allows PDF.js / epub.js to access Google Drive
# through the same Vercel domain.
# ---------------------------------------------------------

@app.route("/book")
def book_proxy():

    url = request.args.get("url", "")

    if not url:
        abort(400, "Book URL is missing.")

    if not is_allowed_book_url(url):

        abort(
            403,
            "Only supported Google Drive URLs are allowed."
        )


    # Forward browser Range header.
    # PDF.js uses this for partial PDF loading.

    headers = {}

    range_header = request.headers.get(
        "Range"
    )

    if range_header:

        headers["Range"] = range_header


    try:

        response = requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=30,
            allow_redirects=True
        )

    except requests.RequestException as e:

        print(
            "BOOK PROXY ERROR:",
            str(e)
        )

        abort(
            502,
            "Unable to fetch book."
        )


    if response.status_code >= 400:

        abort(
            response.status_code,
            "Unable to fetch book."
        )


    # -----------------------------------------------------
    # Determine content type
    # -----------------------------------------------------

    content_type = response.headers.get(
        "Content-Type",
        "application/octet-stream"
    )


    # Google sometimes returns HTML for an error/download page.
    # Don't pretend it is a book.
    if "text/html" in content_type.lower():

        print(
            "Google Drive returned HTML instead of book."
        )

        abort(
            502,
            "Google Drive did not return the book file."
        )


    # -----------------------------------------------------
    # Response headers
    # -----------------------------------------------------

    response_headers = {

        "Content-Type": content_type,

        "Accept-Ranges": "bytes",

        "Cache-Control":
            "public, max-age=3600"
    }


    for header in [
        "Content-Length",
        "Content-Range",
        "ETag",
        "Last-Modified"
    ]:

        value = response.headers.get(header)

        if value:

            response_headers[header] = value


    # -----------------------------------------------------
    # Stream file to browser
    # -----------------------------------------------------

    def generate():

        try:

            for chunk in response.iter_content(
                chunk_size=1024 * 256
            ):

                if chunk:

                    yield chunk

        finally:

            response.close()


    return Response(
        generate(),
        status=response.status_code,
        headers=response_headers
    )


# ---------------------------------------------------------
# Vercel entry point
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )
