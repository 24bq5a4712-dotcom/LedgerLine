import os
import tempfile
import unittest

fd, TEST_DB = tempfile.mkstemp(suffix=".db")
os.close(fd)
os.environ["LEDGERLINE_DB"] = TEST_DB
os.environ["JWT_SECRET_KEY"] = "ledgerline-test-secret-at-least-32-characters-long"

from app import app


class LedgerLineTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.user = self.login("aarav@ledgerline.demo", "Demo@1234")
        self.headers = {"Authorization": "Bearer " + self.user["token"]}

    def login(self, email, password):
        response = self.client.post("/api/auth/login", json={"email": email, "password": password})
        return response.get_json() if response.status_code == 200 else {}

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_login_and_dashboard_require_valid_jwt(self):
        self.assertEqual(self.client.get("/api/dashboard").status_code, 401)
        response = self.client.get("/api/dashboard", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["email"], "aarav@ledgerline.demo")

    def test_invalid_login_is_denied(self):
        response = self.client.post("/api/auth/login", json={"email": "aarav@ledgerline.demo", "password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid email or password", response.get_json()["error"])

    def test_registration_validation_and_duplicate_email(self):
        invalid = self.client.post("/api/auth/register", json={"name": "A", "email": "bad", "password": "weak"})
        self.assertEqual(invalid.status_code, 400)
        duplicate = self.client.post("/api/auth/register", json={"name": "Aarav Copy", "email": "aarav@ledgerline.demo", "password": "Strong123"})
        self.assertEqual(duplicate.status_code, 409)

    def test_transfer_updates_balance_and_history(self):
        before = self.client.get("/api/dashboard", headers=self.headers).get_json()["user"]["balanceCents"]
        response = self.client.post("/api/transfers", headers=self.headers, json={
            "recipientId": 2, "amount": 1.25, "description": "Test payment"
        })
        self.assertEqual(response.status_code, 201)
        after = self.client.get("/api/dashboard", headers=self.headers).get_json()["user"]["balanceCents"]
        self.assertEqual(after, before - 125)
        history = self.client.get("/api/transactions", headers=self.headers).get_json()
        self.assertTrue(any(item["id"] == response.get_json()["transactionId"] for item in history))

    def test_transfer_rejects_self_and_excess_amount(self):
        self_response = self.client.post("/api/transfers", headers=self.headers, json={"recipientId": 1, "amount": 1})
        self.assertEqual(self_response.status_code, 400)
        excess = self.client.post("/api/transfers", headers=self.headers, json={"recipientId": 2, "amount": 999999})
        self.assertEqual(excess.status_code, 422)

    def test_transaction_detail_is_owner_authorized_and_logout_is_audited(self):
        transfer = self.client.post("/api/transfers", headers=self.headers, json={
            "recipientId": 2, "amount": 1, "description": "Detail test"
        })
        transaction_id = transfer.get_json()["transactionId"]
        detail = self.client.get(f"/api/transactions/{transaction_id}", headers=self.headers)
        self.assertEqual(detail.status_code, 200)
        other = self.client.post("/api/auth/register", json={
            "name": "Unauthorized Viewer", "email": "other@ledgerline.demo", "password": "Other123"
        }).get_json()
        other_headers = {"Authorization": "Bearer " + other["token"]}
        denied = self.client.get(f"/api/transactions/{transaction_id}", headers=other_headers)
        self.assertEqual(denied.status_code, 403)
        logout = self.client.post("/api/auth/logout", headers=self.headers)
        self.assertEqual(logout.status_code, 200)

    def test_admin_routes_reject_regular_user(self):
        audit = self.client.get("/api/admin/audit", headers=self.headers)
        users = self.client.get("/api/admin/users", headers=self.headers)
        self.assertEqual(audit.status_code, 403)
        self.assertEqual(users.status_code, 403)

    def test_admin_can_view_audit_records(self):
        login = self.login("admin@ledgerline.demo", "Admin@1234")
        headers = {"Authorization": "Bearer " + login["token"]}
        response = self.client.get("/api/admin/audit", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json())


if __name__ == "__main__":
    unittest.main()
