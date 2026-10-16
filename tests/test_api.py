import unittest
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
            {"Range": "bytes=0-3"}
        )


if __name__ == "__main__":
    unittest.main()