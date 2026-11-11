import unittest
import json
import tempfile
import zipfile
import hashlib
import hmac
from pathlib import Path

from ai_engineer_pathfinder.arrays import Array, OrderedArray, OrderedRecordArray, chapter2_demo
from ai_engineer_pathfinder.career import (
    JobLead,
    draft_application,
    filter_and_rank,
    load_leads,
    update_history,
    write_digest,
    write_drafts,
)
from ai_engineer_pathfinder.models import Skill
from ai_engineer_pathfinder.planner import Pathfinder
from ai_engineer_pathfinder.structures import PriorityQueue, SkillCatalog, SkillGraph
from ai_engineer_pathfinder.web_app import WEBXR_PAGE, make_handler
from ai_engineer_pathfinder.sorting import SortableArray, chapter3_demo
from ai_engineer_pathfinder.stacks_queues import (
    CircularQueue,
    Deque,
    Stack,
    StablePriorityQueue,
    chapter4_demo,
    check_delimiters,
    evaluate_expression,
    infix_to_postfix,
    is_palindrome,
)
from ai_engineer_pathfinder.linked_lists import (
    CircularList,
    CircularQueueADT,
    CircularStack,
    DoublyLinkedList,
    DoubleEndedList,
    FibonacciIterator,
    LinkQueue,
    LinkStack,
    LinkedDeque,
    LinkedList,
    LinkedPriorityQueue,
    OrderedList,
    TwoLevelPriorityQueue,
    chapter5_demo,
)
from ai_engineer_pathfinder.income import sync_income_leads, write_income_bundle
from ai_engineer_pathfinder.monitor import run_monitor
from ai_engineer_pathfinder.product import build_release
from ai_engineer_pathfinder.finance import write_fuel_report
from ai_engineer_pathfinder.payments import PaymentWebhookError, ingest_lemonsqueezy_event
from ai_engineer_pathfinder.finance import summarize_ledger


class DataStructureTests(unittest.TestCase):
    def setUp(self):
        self.python = Skill("python", "Python", "programming", "code", importance=10)
        self.ml = Skill(
            "ml",
            "Machine Learning",
            "machine learning",
            "models",
            prerequisites=("python",),
            importance=9,
        )
        self.catalog = SkillCatalog([self.python, self.ml])

    def test_hash_table_lookup_and_search(self):
        self.assertIs(self.catalog.get("python"), self.python)
        self.assertEqual([self.ml], self.catalog.search("learning"))

    def test_graph_breadth_first_path(self):
        graph = SkillGraph([self.python, self.ml])
        self.assertEqual(["python", "ml"], graph.learning_path(["python"], "ml"))

    def test_priority_queue_returns_highest_importance_first(self):
        queue = PriorityQueue()
        queue.push(self.ml)
        queue.push(self.python)
        self.assertEqual("python", queue.pop().id)


class PathfinderTests(unittest.TestCase):
    def setUp(self):
        self.pathfinder = Pathfinder(
            [
                Skill("python", "Python", "programming", "code", importance=10),
                Skill("data", "Data", "data", "data", ("python",), importance=8),
                Skill("ml", "ML", "machine learning", "models", ("data",), importance=9),
            ]
        )

    def test_next_skills_respect_prerequisites(self):
        self.assertEqual(["data"], [skill.id for skill in self.pathfinder.next_skills(["python"])])

    def test_path_to_target(self):
        self.assertEqual(
            ["python", "data", "ml"],
            [skill.id for skill in self.pathfinder.path_to("ml", ["python"])],
        )

    def test_web_handler_factory_returns_a_request_handler(self):
        handler = make_handler(self.pathfinder)
        self.assertTrue(hasattr(handler, "do_GET"))

    def test_webxr_page_contains_all_chapter_stations(self):
        for chapter in range(1, 6):
            self.assertIn(f"Chapter {chapter}", WEBXR_PAGE)
        self.assertIn("VRButton", WEBXR_PAGE)
        self.assertIn("requestPointerLock", WEBXR_PAGE)
        self.assertIn("updateVRLocomotion", WEBXR_PAGE)
        self.assertIn("teleportFromRay", WEBXR_PAGE)
        self.assertIn("RUN", WEBXR_PAGE)


class CareerAutomationTests(unittest.TestCase):
    def test_leads_rank_title_matches_and_filter_query(self):
        leads = [
            JobLead("test", "AI Python Engineer", "Acme", "https://example.com/1", description="Build APIs"),
            JobLead("test", "Marketing Manager", "Other", "https://example.com/2", description="Marketing"),
        ]
        ranked = filter_and_rank(leads, "python")
        self.assertEqual(1, len(ranked))
        self.assertEqual("AI Python Engineer", ranked[0][2].title)
        self.assertIn("python", ranked[0][1])

    def test_entry_level_filter_removes_senior_titles(self):
        leads = [
            JobLead("test", "Senior AI Engineer", "Acme", "https://example.com/1"),
            JobLead("test", "AI Engineer", "Acme", "https://example.com/2"),
        ]
        ranked = filter_and_rank(leads, "AI", ("senior",))
        self.assertEqual(["AI Engineer"], [item[2].title for item in ranked])

    def test_ranked_leads_deduplicate_shared_listing_urls(self):
        lead = JobLead("feed-a", "AI Engineer", "Acme", "https://example.com/same")
        duplicate = JobLead("feed-b", "AI Engineer", "Acme", "https://example.com/same")
        ranked = filter_and_rank([lead, duplicate], "AI")
        self.assertEqual(1, len(ranked))

    def test_engineering_only_filter_rejects_non_engineering_titles(self):
        leads = [
            JobLead("test", "AI Marketing Manager", "Acme", "https://example.com/marketing"),
            JobLead("test", "AI Application Engineer", "Acme", "https://example.com/engineering"),
        ]
        ranked = filter_and_rank(leads, "AI", engineering_only=True)
        self.assertEqual(["AI Application Engineer"], [item[2].title for item in ranked])

    def test_contract_first_prefers_contracts_and_skips_screening_barriers(self):
        leads = [
            JobLead("test", "AI Engineer", "Employee Co", "https://example.com/employee", description="Full-time role with background check"),
            JobLead("test", "AI Engineer Contractor", "Client Co", "https://example.com/contract", description="Contract project using Python APIs"),
        ]
        ranked = filter_and_rank(leads, "AI", contract_first=True)
        self.assertEqual(["AI Engineer Contractor"], [item[2].title for item in ranked])
        self.assertIn("contract-friendly", ranked[0][1])

    def test_load_leads_and_application_draft_are_local_and_truthful(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "leads.json"
            path.write_text(
                json.dumps([{"source": "fixture", "title": "RAG Engineer", "company": "Acme", "url": "https://example.com"}]),
                encoding="utf-8",
            )
            leads = load_leads(path)
        self.assertEqual("RAG Engineer", leads[0].title)
        draft = draft_application(leads[0])
        self.assertIn("Acme team", draft)
        self.assertIn("[insert public link]", draft)

    def test_write_drafts_creates_local_review_files_without_sending(self):
        with tempfile.TemporaryDirectory() as directory:
            lead = JobLead("fixture", "AI Engineer", "Example Co", "https://example.com/job")
            paths = write_drafts([(8, ["ai"], lead)], Path(directory))
            self.assertEqual(1, len(paths))
            content = paths[0].read_text(encoding="utf-8")
        self.assertIn("https://example.com/job", content)
        self.assertIn("Application draft", content)

    def test_income_bundle_and_offline_sync_create_sellable_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_income_bundle(root / "bundle")
            lead = JobLead("fixture", "AI Engineer Contractor", "Example Co", "https://example.com/job", description="Contract Python API project")
            count, errors = sync_income_leads(root / "pipeline", leads=[lead])
            self.assertEqual(1, count)
            self.assertEqual([], errors)
            self.assertGreaterEqual(len(paths), 6)
            self.assertTrue((root / "pipeline" / "proposals").is_dir())
            self.assertIn("Invoice", (root / "bundle" / "invoice_template.md").read_text(encoding="utf-8"))

    def test_fuel_report_starts_conservatively_without_verified_revenue(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "finance"
            summary = write_fuel_report(output)
            self.assertEqual(0, summary.cleared_revenue_cents)
            self.assertEqual(0, summary.fuel_budget_cents)
            self.assertIn("automatic transfer", (output / "latest.md").read_text(encoding="utf-8"))

    def test_signed_payment_webhook_records_revenue_once(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.json"
            payload = {
                "meta": {"event_name": "order_created"},
                "data": {
                    "id": "order-1",
                    "attributes": {
                        "currency": "USD",
                        "status": "paid",
                        "refunded": False,
                        "subtotal": 2900,
                        "created_at": "2026-08-15T18:00:00Z",
                    },
                },
            }
            raw = json.dumps(payload).encode("utf-8")
            secret = "test-secret"
            signature = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
            self.assertEqual("recorded", ingest_lemonsqueezy_event(raw, signature, secret, ledger))
            self.assertEqual("duplicate", ingest_lemonsqueezy_event(raw, signature, secret, ledger))
            summary = summarize_ledger(ledger)
            self.assertEqual(2900, summary.cleared_revenue_cents)
            self.assertEqual(1450, summary.fuel_budget_cents)
            with self.assertRaises(PaymentWebhookError):
                ingest_lemonsqueezy_event(raw, "bad", secret, ledger)

    def test_product_release_is_sanitized_and_distributable(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path, manifest_path, files = build_release(Path(directory) / "toolkit.zip")
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                archive_text = "\n".join(name for name in names)
            manifest = manifest_path.read_text(encoding="utf-8")
        self.assertTrue(files)
        self.assertIn("store_page_draft.md", archive_text)
        self.assertIn("ai_engineer_pathfinder/career.py", archive_text)
        self.assertNotIn("/home/anon", archive_text)
        self.assertNotIn("career_output", manifest)

    def test_history_returns_only_unseen_listings_and_digest_is_local(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lead = JobLead("fixture", "AI Engineer", "Example Co", "https://example.com/job")
            ranked = [(8, ["ai"], lead)]
            history = root / "history.json"
            self.assertEqual(1, len(update_history(ranked, history)))
            self.assertEqual(0, len(update_history(ranked, history)))
            digest = root / "latest.md"
            write_digest(ranked, digest)
            content = digest.read_text(encoding="utf-8")
        self.assertIn("Quiet Systems career digest", content)
        self.assertIn("https://example.com/job", content)

    def test_monitor_writes_local_status_and_deduplicates_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lead = JobLead(
                "fixture",
                "AI Engineer Contractor",
                "Example Co",
                "https://example.com/monitor-job",
                description="Contract Python API project",
            )
            first = run_monitor(root, leads=[lead], min_score=0)
            second = run_monitor(root, leads=[lead], min_score=0)
            self.assertEqual(1, first.new_leads)
            self.assertEqual(0, second.new_leads)
            self.assertEqual(1, json.loads((root / "status.json").read_text())["total_matches"])
            self.assertTrue((root / "latest.md").exists())
            self.assertTrue((root / "new_leads.json").exists())


class ArrayChapterTests(unittest.TestCase):
    def test_array_core_operations_and_capacity(self):
        array = Array[int](4)
        for item in [77, 12, 44, 3]:
            array.insert(item)
        self.assertEqual([77, 12, 44, 3], list(array))
        self.assertEqual(2, array.find(44))
        self.assertEqual(44, array.search(44))
        self.assertTrue(array.delete(12))
        self.assertEqual([77, 44, 3], list(array))
        array.insert(99)
        with self.assertRaises(OverflowError):
            array.insert(100)

    def test_array_numeric_max_and_duplicate_removal(self):
        array = Array[int | str](8)
        for item in [3, "model", 11, 3, 0, 11]:
            array.insert(item)
        self.assertEqual(11, array.get_max_num())
        self.assertEqual(11, array.delete_max_num())
        self.assertEqual(1, array.remove_dupes())
        self.assertEqual([3, "model", 0, 11], list(array))

    def test_ordered_array_sorts_and_binary_searches(self):
        array = OrderedArray[int](6)
        for item in [77, 12, 44, 3, 12]:
            array.insert(item)
        self.assertEqual([3, 12, 12, 44, 77], list(array))
        self.assertEqual(3, array.find(44))
        self.assertIsNone(array.search(46))
        self.assertLessEqual(array.last_stats.comparisons, 3)
        self.assertTrue(array.delete(12))
        self.assertEqual([3, 12, 44, 77], list(array))

    def test_ordered_record_array_deletes_exact_duplicate_and_expands(self):
        key = lambda record: record[1]
        array = OrderedRecordArray[tuple[str, float]](1, key=key)
        records = [("a", 3.1), ("b", 7.5), ("c", 3.1)]
        for record in records:
            array.insert(record)
        self.assertGreaterEqual(array.capacity, 3)
        self.assertEqual([3.1, 3.1, 7.5], [record[1] for record in array])
        self.assertEqual(set(records), set(array))
        self.assertTrue(array.delete(("c", 3.1)))
        self.assertEqual([("a", 3.1), ("b", 7.5)], list(array))
        self.assertFalse(array.delete(("missing", 3.1)))

    def test_ordered_record_array_merges_only_matching_key_function(self):
        key = lambda record: record[1]
        left = OrderedRecordArray[tuple[str, int]](2, key=key)
        right = OrderedRecordArray[tuple[str, int]](2, key=key)
        for record in [("a", 1), ("c", 5)]:
            left.insert(record)
        for record in [("b", 3), ("d", 7)]:
            right.insert(record)
        left.merge(right)
        self.assertEqual([("a", 1), ("b", 3), ("c", 5), ("d", 7)], list(left))

        different_key = lambda record: record[1]
        incompatible = OrderedRecordArray[tuple[str, int]](2, key=different_key)
        with self.assertRaises(ValueError):
            left.merge(incompatible)

    def test_chapter2_demo_mentions_both_search_orders(self):
        demo = chapter2_demo()
        self.assertIn("O(N)", demo)
        self.assertIn("O(log N)", demo)


class SortingChapterTests(unittest.TestCase):
    @staticmethod
    def make_array(values):
        array = SortableArray(len(values))
        for value in values:
            array.insert(value)
        return array

    def test_all_three_simple_sorts_produce_sorted_output(self):
        values = [77, 12, 44, 3, 99, 17]
        expected = sorted(values)
        for method_name in ("bubble_sort", "selection_sort", "insertion_sort"):
            with self.subTest(method=method_name):
                array = self.make_array(values)
                stats = getattr(array, method_name)()
                self.assertEqual(expected, list(array))
                self.assertGreater(stats.comparisons, 0)

    def test_sort_operation_profiles_match_the_chapter(self):
        bubble = self.make_array([5, 4, 3, 2, 1])
        bubble_stats = bubble.bubble_sort()
        self.assertEqual(10, bubble_stats.comparisons)

        selection = self.make_array([5, 4, 3, 2, 1])
        selection_stats = selection.selection_sort()
        self.assertEqual(10, selection_stats.comparisons)
        self.assertEqual(4, selection_stats.swaps)

        insertion = self.make_array([1, 2, 3, 4, 5])
        insertion_stats = insertion.insertion_sort()
        self.assertEqual(4, insertion_stats.comparisons)
        self.assertEqual(8, insertion_stats.copies)

    def test_odd_even_sort_and_sorted_deduplication(self):
        array = self.make_array([9, 2, 7, 2, 4, 9, 1])
        array.odd_even_sort()
        self.assertEqual([1, 2, 2, 4, 7, 9, 9], list(array))
        self.assertEqual(2, array.deduplicate())
        self.assertEqual([1, 2, 4, 7, 9], list(array))

    def test_chapter3_demo_reports_sorting_concepts(self):
        demo = chapter3_demo()
        self.assertIn("Bubble sort", demo)
        self.assertIn("Selection sort", demo)
        self.assertIn("Insertion sort", demo)
        self.assertIn("O(N^2)", demo)
        self.assertIn("Nearly sorted", demo)


class StackQueueChapterTests(unittest.TestCase):
    def test_stack_is_lifo_and_enforces_capacity(self):
        stack = Stack[str](2)
        stack.push("first")
        stack.push("second")
        self.assertEqual("second", stack.peek())
        with self.assertRaises(OverflowError):
            stack.push("third")
        self.assertEqual("second", stack.pop())
        self.assertEqual("first", stack.pop())
        with self.assertRaises(IndexError):
            stack.pop()

    def test_circular_queue_preserves_fifo_order_after_wraparound(self):
        queue = CircularQueue[str](4)
        for item in ("A", "B", "C"):
            queue.insert(item)
        self.assertEqual("A", queue.remove())
        queue.insert("D")
        queue.insert("E")
        self.assertEqual(["B", "C", "D", "E"], list(queue))
        self.assertEqual("B", queue.peek())

    def test_deque_supports_both_ends(self):
        deque = Deque[str](4)
        deque.insert_right("middle")
        deque.insert_left("left")
        deque.insert_right("right")
        self.assertEqual(["left", "middle", "right"], list(deque))
        self.assertEqual("right", deque.remove_right())
        self.assertEqual("left", deque.remove_left())
        self.assertEqual(["middle"], list(deque))

    def test_priority_queue_is_stable_for_equal_priorities(self):
        queue = StablePriorityQueue[tuple[int, str]](4, priority=lambda item: item[0])
        for item in ((1, "Don"), (0, "Ada"), (1, "Len"), (0, "Joe")):
            queue.insert(item)
        self.assertEqual((0, "Ada"), queue.peek())
        self.assertEqual(
            [(0, "Ada"), (0, "Joe"), (1, "Don"), (1, "Len")],
            [queue.remove() for _ in range(len(queue))],
        )

    def test_delimiters_palindromes_and_expression_parsing(self):
        self.assertEqual((True, []), check_delimiters("a{b[c](d)}"))
        balanced, errors = check_delimiters("a{b(c]d}")
        self.assertFalse(balanced)
        self.assertTrue(errors)
        self.assertTrue(is_palindrome("A man, a plan, a canal, Panama."))
        self.assertFalse(is_palindrome("data structures"))

        self.assertEqual("A B C * +", infix_to_postfix("A+B*C"))
        postfix, result, variables = evaluate_expression(
            "(A = 3 + 4 * 5) + (B = 7 * 6) + B / A"
        )
        self.assertEqual("A 3 4 5 * + = B 7 6 * = + B A / +", postfix)
        self.assertAlmostEqual(66.8260869565, result)
        self.assertEqual({"A": 23, "B": 42}, variables)

    def test_chapter4_demo_mentions_access_order_and_postfix(self):
        demo = chapter4_demo()
        self.assertIn("Stack pop order", demo)
        self.assertIn("Circular queue", demo)
        self.assertIn("Priority queue", demo)
        self.assertIn("Postfix", demo)


class LinkedListChapterTests(unittest.TestCase):
    def test_singly_linked_list_operations_and_explicit_iterator(self):
        linked = LinkedList[int]()
        for value in (1, 2, 3):
            linked.insert(value)
        self.assertEqual([3, 2, 1], list(linked))
        self.assertTrue(linked.insert_after(2, 4))
        self.assertEqual([3, 2, 4, 1], list(linked))
        self.assertEqual(4, linked.search(4))
        self.assertEqual(2, linked.delete(2))
        self.assertEqual([3, 4, 1], list(linked))

        iterator = linked.iterator()
        self.assertEqual([3, 4, 1], [iterator.next(), iterator.next(), iterator.next()])
        with self.assertRaises(StopIteration):
            iterator.next()

    def test_double_ended_and_ordered_lists(self):
        double = DoubleEndedList[int]()
        double.insert(2)
        double.insert(1)
        double.insert_last(3)
        self.assertEqual([1, 2, 3], list(double))
        self.assertEqual(3, double.last())
        self.assertEqual(3, double.delete(3))
        self.assertEqual(2, double.last())

        ordered = OrderedList[int]()
        for value in (9, -2, 625, -64, 1):
            ordered.insert(value)
        self.assertEqual([-64, -2, 1, 9, 625], list(ordered))
        self.assertEqual(-2, ordered.find(-9).get_data())
        self.assertIsNone(ordered.search(999))
        self.assertEqual(1, ordered.delete(1))

    def test_doubly_linked_list_supports_reverse_traversal_and_middle_updates(self):
        linked = DoublyLinkedList[str]()
        linked.insert_last("A")
        linked.insert_last("C")
        self.assertTrue(linked.insert_after("A", "B"))
        self.assertEqual(["A", "B", "C"], list(linked))
        self.assertEqual(["C", "B", "A"], list(linked.iter_reverse()))
        self.assertEqual("B", linked.delete("B"))
        self.assertEqual("A", linked.delete_first())
        self.assertEqual("C", linked.delete_last())
        self.assertTrue(linked.is_empty())

    def test_circular_list_and_linked_adts_preserve_access_order(self):
        circular = CircularList[str]()
        for value in ("A", "B", "C"):
            circular.insert_last(value)
        self.assertEqual(["A", "B", "C"], list(circular))
        circular.step()
        self.assertEqual("B", circular.first())
        self.assertEqual("B", circular.delete_first())
        self.assertEqual("C", circular.search("C"))

        stack = LinkStack[int]()
        queue = LinkQueue[int]()
        for value in (1, 2, 3):
            stack.push(value)
            queue.insert(value)
        self.assertEqual([3, 2, 1], [stack.pop(), stack.pop(), stack.pop()])
        self.assertEqual([1, 2, 3], [queue.remove(), queue.remove(), queue.remove()])

        linked_deque = LinkedDeque[int]()
        linked_deque.insert_left(2)
        linked_deque.insert_left(1)
        linked_deque.insert_right(3)
        self.assertEqual([1, 2, 3], list(linked_deque))
        self.assertEqual(3, linked_deque.remove_right())

        priority = LinkedPriorityQueue[tuple[int, str], int](priority=lambda item: item[0])
        for item in ((2, "low"), (0, "high"), (1, "middle")):
            priority.insert(item)
        self.assertEqual([(0, "high"), (1, "middle"), (2, "low")], list(priority))
        self.assertEqual((0, "high"), priority.remove())

        circular_stack = CircularStack[int]()
        circular_queue = CircularQueueADT[int]()
        circular_stack.push(1)
        circular_stack.push(2)
        circular_queue.insert(1)
        circular_queue.insert(2)
        self.assertEqual(2, circular_stack.pop())
        self.assertEqual(1, circular_queue.remove())

    def test_two_level_priority_queue_and_bidirectional_fibonacci(self):
        priority = TwoLevelPriorityQueue[str, int]()
        priority.insert("later high", 0)
        priority.insert("low", 2)
        priority.insert("earlier high", 0)
        self.assertEqual([0, 2], list(priority.priorities()))
        self.assertEqual("later high", priority.remove())
        self.assertEqual("earlier high", priority.remove(0))
        self.assertEqual("low", priority.remove())

        fibonacci = FibonacciIterator()
        self.assertEqual([1, 1, 2, 3, 5], [fibonacci.next() for _ in range(5)])
        self.assertEqual(5, fibonacci.previous())
        self.assertEqual(5, fibonacci.next())
        fresh = FibonacciIterator()
        with self.assertRaises(StopIteration):
            fresh.previous()

    def test_chapter5_demo_mentions_link_variants_and_iterators(self):
        demo = chapter5_demo()
        self.assertIn("Singly linked list", demo)
        self.assertIn("Ordered linked list", demo)
        self.assertIn("Doubly linked", demo)
        self.assertIn("Fibonacci iterator", demo)


if __name__ == "__main__":
    unittest.main()
