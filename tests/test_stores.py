"""Store-level tests for hardware sets and project hardware counts."""

import unittest

from app.hardware import ConflictError, NotFoundError
from app.hardware_sets import HardwareSetStore
from app.projects import ProjectStore, checked_out
from tests.fakes import FakeDatabase


class HardwareSetStoreTests(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase()
        self.sets = HardwareSetStore(self.database)
        self.projects = ProjectStore(self.database)

    def test_fresh_database_gets_two_sets_at_full_capacity(self):
        listed = self.sets.list()
        self.assertEqual([s["_id"] for s in listed], ["HWSet1", "HWSet2"])
        self.assertEqual([(s["capacity"], s["available"]) for s in listed], [(100, 100), (100, 100)])
        self.sets.list()
        self.assertEqual(len(self.database["hardware_sets"].documents), 2)

    def test_take_reduces_and_refuses_more_than_available(self):
        self.assertEqual(self.sets.take("HWSet1", 30)["available"], 70)
        with self.assertRaises(ConflictError) as raised:
            self.sets.take("HWSet1", 71)
        self.assertIn("only 70 available", raised.exception.message)
        self.assertEqual(self.sets.get("HWSet1")["available"], 70)
        self.assertEqual(self.sets.take("HWSet1", 70)["available"], 0)
        with self.assertRaises(NotFoundError):
            self.sets.take("HWSet9", 1)

    def test_give_back_increases(self):
        self.sets.take("HWSet2", 10)
        self.assertEqual(self.sets.give_back("HWSet2", 4)["available"], 94)

    def test_project_counts_require_membership_and_enough_units(self):
        self.projects.create("Team", "ada", "team1")
        self.assertIsNone(self.projects.add_hardware("team1", "grace", "HWSet1", 5))
        self.assertEqual(checked_out(self.projects.add_hardware("team1", "ada", "HWSet1", 5)), {"HWSet1": 5})
        self.projects.join("team1", "grace")
        self.assertIsNone(self.projects.remove_hardware("team1", "grace", "HWSet1", 6))
        self.assertIsNone(self.projects.remove_hardware("team1", "grace", "HWSet2", 1))
        self.assertEqual(checked_out(self.projects.remove_hardware("team1", "grace", "HWSet1", 5)), {})


if __name__ == "__main__":
    unittest.main()
