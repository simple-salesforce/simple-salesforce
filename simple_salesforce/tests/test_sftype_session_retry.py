"""An expired Salesforce session stops retrying."""

import unittest

from simple_salesforce.api import SFType
from simple_salesforce.exceptions import SalesforceExpiredSession

URL = "https://example.my.salesforce.com/services/data/v59.0/sobjects/Contact/003"


class TestSFTypeSessionRetry(unittest.TestCase):
    def test_an_expired_session_stops_after_the_retry_limit(self):
        class Parent:
            session_id = "old-session"
            _salesforce_login_partial = staticmethod(
                lambda: ("new-session", "example.my.salesforce.com")
            )

            def _refresh_session(self):
                self.session_id = "new-session"

        calls = []

        class Session:
            def request(self, method, url, headers=None, **kwargs):
                calls.append(headers["Authorization"])
                if len(calls) > 4:
                    raise AssertionError("retry did not stop")
                response = type("Response", (), {})()
                response.status_code = 401
                response.headers = {}
                response.url = url
                response.json = lambda: [{
                    "errorCode": "INVALID_SESSION_ID",
                    "message": "Session expired or invalid",
                }]
                return response

        with self.assertRaises(SalesforceExpiredSession):
            SFType(
                "Contact",
                "old-session",
                "example.my.salesforce.com",
                session=Session(),
                salesforce=Parent(),
            )._call_salesforce("GET", URL, max_retries=3)
        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[0], "Bearer old-session")
        self.assertEqual(calls[-1], "Bearer new-session")
