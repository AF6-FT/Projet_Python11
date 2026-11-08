"""Tests de base pour le parsing et les agrégations du pipeline."""

import tempfile
import unittest
from pathlib import Path

from pipeline.processing import parse_auth_line
from serving.dashboard import build_dashboard
from storage.database import EventStore
from storage.models import AuthEvent


class ParseAuthLineTests(unittest.TestCase):
    def test_parses_successful_login(self) -> None:
        line = (
            "May 12 10:11:12 host sshd[123]: Accepted password for admin "
            "from 203.0.113.8 port 22 ssh2"
        )
        event = parse_auth_line(line, year=2026)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.username, "admin")
        self.assertEqual(event.status, "Success")
        self.assertEqual(event.ip, "203.0.113.8")

    def test_parses_invalid_user_failure_and_repetition_count(self) -> None:
        line = (
            "May 12 10:11:12 host sshd[123]: message repeated 3 times: "
            "[Failed password for invalid user guest from 203.0.113.8 port 22 ssh2]"
        )
        event = parse_auth_line(line, year=2026)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.username, "guest")
        self.assertEqual(event.status, "Failed")
        self.assertEqual(event.attempts, 3)

    def test_parses_invalid_user_notice_for_dashboard(self) -> None:
        line = (
            "May 12 10:11:12 host sshd[123]: Invalid user guest "
            "from 203.0.113.8 port 22"
        )
        event = parse_auth_line(line, year=2026)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.username, "guest")
        self.assertEqual(event.status, "Invalid")

    def test_keeps_invalid_user_failures_with_an_empty_username(self) -> None:
        line = (
            "May 12 10:11:12 host sshd[123]: Failed none for invalid user "
            "from 203.0.113.8 port 22 ssh2"
        )
        event = parse_auth_line(line, year=2026)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.username, "(vide)")
        self.assertEqual(event.status, "Failed")

    def test_ignores_non_authentication_lines(self) -> None:
        self.assertIsNone(
            parse_auth_line(
                "May 12 10:11:12 host sshd[123]: Connection closed by 127.0.0.1",
                year=2026,
            )
        )


class EventStoreTests(unittest.TestCase):
    def test_aggregates_events_for_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory) / "events.sqlite3")
            store.initialize()
            store.replace_events(
                [
                    AuthEvent(
                        "2026-05-12 10:11:12",
                        "203.0.113.8",
                        "admin",
                        "Success",
                        "US",
                    ),
                    AuthEvent(
                        "2026-05-12 10:12:12",
                        "203.0.113.8",
                        "guest",
                        "Invalid",
                        "US",
                        2,
                    ),
                ]
            )
            self.assertEqual(store.successful_attempts_by_user(), [("admin", 1)])
            self.assertEqual(store.failed_attempts_by_country(), [("US", 2)])
            self.assertEqual(store.invalid_user_attempts(10), [("guest", 2)])

    def test_builds_one_dashboard_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = EventStore(root / "events.sqlite3")
            store.initialize()
            store.replace_events(
                [
                    AuthEvent(
                        "2026-05-12 10:11:12",
                        "203.0.113.8",
                        "admin",
                        "Success",
                        "US",
                    ),
                    AuthEvent(
                        "2026-05-12 10:12:12",
                        "203.0.113.8",
                        "guest",
                        "Invalid",
                        "US",
                    ),
                ]
            )
            image = build_dashboard(store, root / "output", show=False)
            self.assertTrue(image.is_file())
            self.assertTrue(image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
