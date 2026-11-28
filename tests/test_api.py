"""Authenticated HTTP acceptance against a real, isolated PostgreSQL schema."""

from dataclasses import replace
import os
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from life_planner.demo import example_plan
from life_planner.storage import migrate
from test_auth import ISSUER, SignedIdentityFixture


TEST_DSN = os.environ.get("PLAN_TEST_DATABASE_URL")
PLAN_URL = "/v1/plans/week"
WINDOW = {"from": "2026-11-23T00:00:00Z", "to": "2026-11-30T00:00:00Z"}
MOVE = {"type": "move_item", "item_id": "gym", "new_start": "2026-11-26T18:00:00-05:00"}


@unittest.skipUnless(TEST_DSN, "HTTP PostgreSQL integration: set PLAN_TEST_DATABASE_URL")
class AuthenticatedApiTests(SignedIdentityFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from apps.api.app import create_app
        self.schema = "lp_api_test_" + uuid4().hex
        with psycopg.connect(TEST_DSN) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)
        options = conninfo_to_dict(TEST_DSN).get("options", "")
        self.dsn = make_conninfo(TEST_DSN, options=options + f" -c search_path={self.schema} -c statement_timeout=10000 -c lock_timeout=5000")
        migrate(self.dsn)
        self.app = create_app(self.settings(database_url=self.dsn))
        self.client = self.enterContext(TestClient(self.app, raise_server_exceptions=False))
        self.alice = {"Authorization": "Bearer " + self.token()}
        self.bob = {"Authorization": "Bearer " + self.token("bob")}
        self.items = [{"id": item.id, "title": item.title, "kind": item.kind,
                       "start": item.start.isoformat(), "end": item.end.isoformat(),
                       "linked_to": item.linked_to, "fixed": item.fixed}
                      for item in example_plan().read_items("demo-user")]

    def drop_schema(self):
        with psycopg.connect(TEST_DSN) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))

    def create_plan(self, headers=None, url=PLAN_URL):
        response = self.client.post(url, headers=headers or self.alice, json={"items": self.items})
        self.assertEqual(201, response.status_code, response.text)
        return response.json()

    def propose(self, headers=None, command=None, url=PLAN_URL):
        response = self.client.post(url + "/proposals", headers=headers or self.alice, json=command or MOVE)
        self.assertEqual(201, response.status_code, response.text)
        return response.json()

    def apply(self, proposal_id, key="request-one", headers=None, body=None, url=PLAN_URL):
        return self.client.post(url + "/proposals/" + proposal_id + "/apply",
                                headers={**(headers or self.alice), "Idempotency-Key": key},
                                json={"confirmed": True} if body is None else body)

    def counts(self):
        with psycopg.connect(self.dsn) as conn:
            return {table: conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
                    for table in ("lp_plans", "lp_proposals", "lp_changes", "lp_receipts", "lp_outbox")}

    def test_discovery_lists_only_authenticated_owner_and_bounded_metadata(self):
        self.assertEqual({"plans": [], "next_after": None},
                         self.client.get("/v1/plans", headers=self.alice).json())
        for headers, plan_ids in ((self.alice, ("a", "c", "e")), (self.bob, ("a", "b", "e"))):
            for plan_id in plan_ids:
                self.create_plan(headers=headers, url="/v1/plans/" + plan_id)
        response = self.client.get("/v1/plans", headers={**self.alice, "X-User-ID": "bob"},
                                   params={"limit": "1", "after": "b"})
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual({"plans": [{"plan_id": "c", "revision": 0}], "next_after": "c"}, response.json())
        self.assertEqual("no-store", response.headers.get("cache-control"))
        self.assertNotIn("items", response.text)
        self.assertNotIn("user_id", response.text)
        final = self.client.get("/v1/plans", headers=self.alice, params={"limit": "1", "after": "c"})
        self.assertEqual({"plans": [{"plan_id": "e", "revision": 0}], "next_after": None}, final.json())
        self.assertEqual(["a", "b", "e"], [plan["plan_id"] for plan in
                         self.client.get("/v1/plans", headers=self.bob).json()["plans"]])

    def test_discovery_revision_is_current_after_confirmed_apply_and_new_app(self):
        from apps.api.app import create_app
        self.create_plan()
        self.assertEqual(200, self.apply(self.propose()["proposal_id"]).status_code)
        with TestClient(create_app(self.settings(database_url=self.dsn))) as restarted:
            response = restarted.get("/v1/plans", headers=self.alice)
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual({"plans": [{"plan_id": "week", "revision": 1}], "next_after": None}, response.json())

    def test_public_health_has_no_private_configuration(self):
        response = self.client.get("/health")
        self.assertEqual(200, response.status_code)
        self.assertNotIn(self.dsn, response.text)
        self.assertNotIn(ISSUER, response.text)
        self.assertNotIn("keys", response.text)

    def test_authenticated_create_preview_apply_and_retry_journey(self):
        created = self.create_plan()
        self.assertEqual(0, created["revision"])
        before = self.client.get(PLAN_URL, headers=self.alice, params=WINDOW)
        self.assertEqual(200, before.status_code, before.text)
        self.assertNotIn("user_id", before.text)
        proposal = self.propose()
        self.assertEqual(0, proposal["base_revision"])
        self.assertEqual({"gym", "meal", "clothes"}, {change["after"]["id"] for change in proposal["changes"]})
        preview = self.client.get(PLAN_URL, headers=self.alice, params=WINDOW)
        self.assertEqual(before.json(), preview.json())
        response = self.apply(proposal["proposal_id"])
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(1, response.json()["applied_revision"])
        retry = self.apply(proposal["proposal_id"])
        self.assertEqual(response.json(), retry.json())
        after = self.client.get(PLAN_URL, headers=self.alice, params=WINDOW)
        self.assertEqual(1, after.json()["revision"])
        self.assertNotEqual(before.json()["items"], after.json()["items"])
        self.assertEqual("no-store", after.headers.get("cache-control"))
        self.assertEqual({"lp_plans": 1, "lp_proposals": 1, "lp_changes": 1, "lp_receipts": 1, "lp_outbox": 1}, self.counts())

    def test_unauthenticated_and_invalid_signed_requests_cannot_write(self):
        tokens = (None, "not-a-token", self.token(key=self.wrong_key), self.token(changes={"aud": "another-api"}), self.token(headers={"typ": "JWT"}))
        for token in tokens:
            headers = {} if token is None else {"Authorization": "Bearer " + token}
            response = self.client.post(PLAN_URL, headers=headers, json={"items": self.items})
            with self.subTest(token=token):
                self.assertEqual(401, response.status_code, response.text)
                self.assertIn("bearer", response.headers.get("www-authenticate", "").lower())
                if token:
                    self.assertNotIn(token, response.text)
        self.assertEqual(0, self.counts()["lp_plans"])

    def test_other_identity_get_propose_apply_match_missing_resource_responses(self):
        self.create_plan()
        proposal = self.propose()
        other_get = self.client.get(PLAN_URL, headers=self.bob, params=WINDOW)
        missing_get = self.client.get("/v1/plans/missing", headers=self.bob, params=WINDOW)
        for response in (other_get, missing_get,
                         self.client.post(PLAN_URL + "/proposals", headers=self.bob, json=MOVE),
                         self.apply(proposal["proposal_id"], headers=self.bob)):
            self.assertEqual(404, response.status_code, response.text)
            self.assertNotIn("Gym", response.text)
        self.assertEqual(other_get.json()["error"]["code"], missing_get.json()["error"]["code"])
        self.assertEqual(other_get.json()["error"]["message"], missing_get.json()["error"]["message"])
        self.assertEqual(0, self.counts()["lp_changes"])

    def test_matching_ids_and_keys_under_two_identities_are_isolated(self):
        self.create_plan()
        self.create_plan(headers=self.bob)
        alice_proposal = self.propose()
        bob_proposal = self.propose(headers=self.bob)
        self.assertEqual(404, self.apply(alice_proposal["proposal_id"], headers=self.bob).status_code)
        self.assertEqual(200, self.apply(alice_proposal["proposal_id"]).status_code)
        bob_before = self.client.get(PLAN_URL, headers=self.bob, params=WINDOW).json()
        self.assertEqual(0, bob_before["revision"])
        self.assertEqual(200, self.apply(bob_proposal["proposal_id"], headers=self.bob).status_code)
        self.assertEqual(2, self.counts()["lp_changes"])

    def test_same_subject_at_another_trusted_issuer_cannot_read_first_issuer_plan(self):
        from apps.api.app import create_app
        self.create_plan()
        issuer = "https://other-identity.example.test"
        app = create_app(replace(self.settings(database_url=self.dsn), issuer=issuer))
        headers = {"Authorization": "Bearer " + self.token(changes={"iss": issuer})}
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(PLAN_URL, headers=headers, params=WINDOW)
        self.assertEqual(404, response.status_code, response.text)

    def test_request_cannot_supply_or_override_owner(self):
        for payload in ({"items": self.items, "user_id": "bob"},
                        {"items": [{**self.items[0], "user_id": "bob"}]}):
            response = self.client.post(PLAN_URL, headers=self.alice, json=payload)
            self.assertEqual(400, response.status_code, response.text)
        self.create_plan(headers={**self.alice, "X-User-ID": "bob"})
        self.assertEqual(404, self.client.get(PLAN_URL, headers=self.bob, params=WINDOW).status_code)
        self.assertEqual(200, self.client.get(PLAN_URL, headers=self.alice, params=WINDOW).status_code)

    def test_create_is_not_an_overwrite_and_fixed_flag_is_strict(self):
        response = self.client.post(PLAN_URL, headers=self.alice,
                                    json={"items": [{**self.items[0], "fixed": "false"}]})
        self.assertEqual(400, response.status_code, response.text)
        self.create_plan()
        duplicate = self.client.post(PLAN_URL, headers=self.alice, json={"items": []})
        self.assertEqual(409, duplicate.status_code, duplicate.text)
        after = self.client.get(PLAN_URL, headers=self.alice, params=WINDOW)
        self.assertEqual(4, len(after.json()["items"]))
        self.assertEqual(0, after.json()["revision"])

    def test_database_unavailable_returns_safe_service_error(self):
        from apps.api.app import create_app
        unavailable = "postgresql://fakeuser:private-password@127.0.0.1:1/missing?connect_timeout=1"
        app = create_app(self.settings(database_url=unavailable))
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(PLAN_URL, headers=self.alice, params=WINDOW)
        self.assertEqual(503, response.status_code, response.text)
        self.assertNotIn("private-password", response.text)
        self.assertNotIn("127.0.0.1", response.text)

    def test_read_window_is_bounded_and_uses_interval_overlap(self):
        self.create_plan()
        for params in ({}, {"from": WINDOW["from"]},
                       {"from": "2026-11-01T00:00:00Z", "to": "2026-12-03T00:00:00Z"},
                       {"from": WINDOW["to"], "to": WINDOW["from"]},
                       {"from": "2026-11-23T00:00:00", "to": WINDOW["to"]}):
            response = self.client.get(PLAN_URL, headers=self.alice, params=params)
            self.assertEqual(400, response.status_code, response.text)
        result = self.client.get(PLAN_URL, headers=self.alice,
                                 params={"from": "2026-11-25T23:30:00Z", "to": "2026-11-26T00:00:00Z"})
        self.assertEqual(200, result.status_code, result.text)
        self.assertEqual(["gym"], [item["id"] for item in result.json()["items"]])

    def test_strict_confirmation_rejects_truthy_values_and_missing_key(self):
        self.create_plan()
        proposal = self.propose()["proposal_id"]
        for value in (False, 1, "true", "false", None, [], {}):
            response = self.apply(proposal, body={"confirmed": value})
            self.assertEqual(400, response.status_code, response.text)
        url = PLAN_URL + "/proposals/" + proposal + "/apply"
        response = self.client.post(url, headers=self.alice, json={"confirmed": True})
        self.assertEqual(400, response.status_code)
        self.assertEqual(0, self.counts()["lp_changes"])

    def test_stale_proposal_and_reused_key_are_conflicts_without_extra_effects(self):
        self.create_plan()
        first = self.propose()["proposal_id"]
        stale = self.propose(command={**MOVE, "new_start": "2026-11-27T18:00:00-05:00"})["proposal_id"]
        self.assertEqual(200, self.apply(first).status_code)
        self.assertEqual(409, self.apply(stale, key="stale-request").status_code)
        second = self.propose(command={**MOVE, "new_start": "2026-11-27T18:00:00-05:00"})["proposal_id"]
        self.assertEqual(409, self.apply(second).status_code)
        self.assertEqual(200, self.apply(second, key="second-request").status_code)
        old_retry = self.apply(first)
        self.assertEqual(1, old_retry.json()["applied_revision"])
        self.assertEqual(2, self.counts()["lp_changes"])

    def test_conflict_errors_do_not_echo_private_item_titles(self):
        self.items[3]["title"] = "PRIVATE-MEDICAL-APPOINTMENT"
        self.create_plan()
        response = self.client.post(PLAN_URL + "/proposals", headers=self.alice,
                                    json={**MOVE, "new_start": "2026-11-26T15:00:00-05:00"})
        self.assertEqual(409, response.status_code, response.text)
        self.assertNotIn("PRIVATE-MEDICAL-APPOINTMENT", response.text)
        self.assertNotIn("study", response.text)
        self.assertEqual(0, self.counts()["lp_proposals"])

    def test_malformed_extra_field_and_unsupported_commands_are_rejected(self):
        self.create_plan()
        for command in ({**MOVE, "new_start": "2026-11-26T18:00:00"},
                        {**MOVE, "type": "delete_everything"}, {**MOVE, "user_id": "bob"},
                        {**MOVE, "item_id": "x" * 129}):
            response = self.client.post(PLAN_URL + "/proposals", headers=self.alice, json=command)
            self.assertEqual(400, response.status_code, response.text)
        malformed = self.client.post(PLAN_URL, headers={**self.alice, "Content-Type": "application/json"}, content='{ "items":')
        self.assertEqual(400, malformed.status_code)
        wrong_type = self.client.post(PLAN_URL, headers={**self.alice, "Content-Type": "text/plain"}, content="secret-text")
        self.assertEqual(415, wrong_type.status_code, wrong_type.text)
        self.assertNotIn("secret-text", wrong_type.text)

    def test_nul_in_item_text_is_rejected_without_persisting_plan(self):
        for field in ("title", "kind"):
            with self.subTest(field=field):
                payload = {"items": [{**item, field: "PRIVATE\x00TEXT"} for item in self.items]}
                response = self.client.post(PLAN_URL, headers=self.alice, json=payload)
                self.assertEqual(400, response.status_code, response.text)
                self.assertNotIn("PRIVATE", response.text)
                self.assertTrue(all(count == 0 for count in self.counts().values()))
                with psycopg.connect(self.dsn) as conn:
                    self.assertEqual(0, conn.execute("SELECT count(*) FROM lp_items").fetchone()[0])

    def test_extreme_dates_and_invalid_offsets_are_safe_client_errors(self):
        self.create_plan()
        before = self.counts()
        invalid = ("0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00",
                   "2026-11-25T18:00:00+24:00", "2026-11-25T18:00:00+00:60")
        for timestamp in invalid:
            with self.subTest(timestamp=timestamp):
                response = self.client.post(PLAN_URL + "/proposals", headers=self.alice,
                                            json={**MOVE, "new_start": timestamp})
                self.assertEqual(400, response.status_code, response.text)
                response = self.client.get(PLAN_URL, headers=self.alice,
                                           params={"from": timestamp, "to": WINDOW["to"]})
                self.assertEqual(400, response.status_code, response.text)
        self.assertEqual(before, self.counts())
        self.assertEqual(0, self.client.get(PLAN_URL, headers=self.alice, params=WINDOW).json()["revision"])

    def test_large_body_is_rejected_with_or_without_content_length(self):
        payload = b'{"items":[],"extra":"' + b'x' * 65536 + b'"}'
        for body in (payload, (payload[index:index+4096] for index in range(0, len(payload), 4096))):
            response = self.client.post(PLAN_URL, headers={**self.alice, "Content-Type": "application/json"}, content=body)
            self.assertEqual(413, response.status_code, response.text)
        self.assertEqual(0, self.counts()["lp_plans"])

    def test_duplicate_authorization_and_idempotency_headers_are_rejected(self):
        auth = self.alice["Authorization"]
        response = self.client.post(PLAN_URL, headers=[("Authorization", auth), ("Authorization", auth)], json={"items": self.items})
        self.assertEqual(401, response.status_code, response.text)
        self.create_plan()
        proposal = self.propose()["proposal_id"]
        response = self.client.post(PLAN_URL + "/proposals/" + proposal + "/apply",
                                    headers=[("Authorization", auth), ("Idempotency-Key", "one"), ("Idempotency-Key", "two")], json={"confirmed": True})
        self.assertEqual(400, response.status_code, response.text)
        self.assertEqual(0, self.counts()["lp_changes"])


if __name__ == "__main__":
    unittest.main()
