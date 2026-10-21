import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from api.index import app


class AccountApiTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.redis = {}

        def command(*parts):
            operation, key, *arguments = parts
            values = self.redis.setdefault(key, {})

            if operation == "HSETNX":
                field, value = arguments
                if field in values:
                    return 0
                values[field] = value
                return 1

            if operation == "HSET":
                for index in range(0, len(arguments), 2):
                    values[arguments[index]] = arguments[index + 1]
                return len(arguments) // 2

            if operation == "HGETALL":
                return [item for pair in values.items() for item in pair]

            if operation == "HEXISTS":
                return int(arguments[0] in values)

            raise AssertionError(f"Unexpected Redis operation: {operation}")

        self.redis_command = patch(
            "api.index.redis_command",
            side_effect=command
        )
        self.redis_command.start()
        self.addCleanup(self.redis_command.stop)

    def test_create_restore_and_update_account(self):
        keyword = "library-private-2026"
        folder_url = "https://drive.google.com/drive/folders/abcdefghijk"
        initial_progress = {"position": "epubcfi(/6/4)", "progress": 20}
        history_entry = {
            "id": "book_123",
            "title": "Sample Book",
            "progress": 20,
            "lastRead": "2026-10-16T12:00:00Z"
        }

        created = self.client.post("/api/account", json={
            "keyword": keyword,
            "folderUrl": folder_url,
            "readingData": {"book_123": initial_progress},
            "history": [history_entry]
        })
        self.assertEqual(created.status_code, 201)

        duplicate = self.client.post("/api/account", json={
            "keyword": keyword,
            "folderUrl": folder_url
        })
        self.assertEqual(duplicate.status_code, 409)

        updated_progress = {"position": "epubcfi(/6/8)", "progress": 40}
        updated = self.client.put("/api/account/progress", json={
            "keyword": keyword,
            "bookId": "book_123",
            "readingData": updated_progress,
            "historyEntry": {**history_entry, "progress": 40}
        })
        self.assertEqual(updated.status_code, 200)

        restored = self.client.post("/api/account/session", json={
            "keyword": keyword
        })
        self.assertEqual(restored.status_code, 200)
        result = restored.get_json()
        self.assertEqual(result["folderUrl"], folder_url)
        self.assertEqual(result["readingData"]["book_123"], updated_progress)
        self.assertEqual(result["history"][0]["progress"], 40)

    def test_rejects_short_keyword(self):
        response = self.client.post("/api/account/session", json={
            "keyword": "too-short"
        })
        self.assertEqual(response.status_code, 400)

    def test_bookshelf_syncs_remote_progress_on_load(self):
        template = Path(__file__).resolve().parents[1] / "templates" / "index.html"
        content = template.read_text()
        self.assertIn("syncAccountProgress", content)
        self.assertIn("await syncAccountProgress()", content)


class DriveProxyTests(unittest.TestCase):
    def test_epub_proxy_preserves_partial_content(self):
        upstream = Mock(
            status_code=206,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": "4",
                "Content-Range": "bytes 0-3/100",
                "Accept-Ranges": "bytes"
            },
            content=b"EPUB"
        )

        with (
            patch("api.index.DRIVE_API_KEY", "drive-test-key"),
            patch("api.index.requests.get", return_value=upstream) as get
        ):
            response = app.test_client().get(
                "/api/file/test_file-123?type=epub",
                headers={"Range": "bytes=0-3"}
            )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content_type, "application/epub+zip")
        self.assertEqual(response.headers["Content-Range"], "bytes 0-3/100")
        self.assertEqual(response.data, b"EPUB")
        self.assertEqual(
            get.call_args.kwargs["headers"],
            {"Accept-Encoding": "identity", "Range": "bytes=0-3"}
        )


class CoverApiTests(unittest.TestCase):
    def setUp(self):
        import api.index as index
        index.COVER_CACHE.clear()
        self.index = index
        self.client = app.test_client()

    def fake_get(self, url, params=None, **kwargs):
        response = Mock()
        response.status_code = 200
        if "openlibrary.org/search.json" in url:
            title = params["title"]
            response.json.return_value = {
                "docs": [{"title": "1984", "cover_i": 7}] if title == "1984" else []
            }
        elif url.startswith("https://covers.openlibrary.org/"):
            response.headers = {"Content-Type": "image/jpeg"}
            response.content = b"x" * 5000
        else:  # Google Books: nothing found
            response.json.return_value = {}
        return response

    def test_clean_title_strips_file_name_noise(self):
        self.assertEqual(
            self.index.clean_title("Needful_Things - Stephen King (z-lib.org).epub"),
            "Needful Things - Stephen King"
        )
        self.assertEqual(
            self.index.split_title_author("Dune - Frank Herbert"),
            ("Dune", "Frank Herbert")
        )

    def test_returns_cover_image_when_found(self):
        with patch("api.index.requests.get", side_effect=self.fake_get):
            response = self.client.get("/api/cover?title=1984.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "image/jpeg")
        self.assertEqual(len(response.data), 5000)

    def test_404_when_no_cover_so_browser_uses_first_page(self):
        with patch("api.index.requests.get", side_effect=self.fake_get):
            response = self.client.get("/api/cover?title=Unknown%20Handbook.pdf")
        self.assertEqual(response.status_code, 404)

    def test_requires_title(self):
        self.assertEqual(self.client.get("/api/cover").status_code, 400)

    def test_outage_is_not_reported_as_missing(self):
        import requests as real_requests
        with patch("api.index.requests.get", side_effect=real_requests.ConnectionError("down")):
            response = self.client.get("/api/cover?title=Dune.pdf")
        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()