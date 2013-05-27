from __future__ import absolute_import

import sys

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

from trac.test import EnvironmentStub
from trac.web.href import Href

from openid import oidutil
from openid.consumer.consumer import SUCCESS, FAILURE, CANCEL, SETUP_NEEDED
from openid.consumer.discover import DiscoveryFailure

from mock import ANY, call, Mock, patch, sentinel

from authopenid.exceptions import (
    AuthenticationFailed,
    AuthenticationCancelled,
    SetupNeeded,
    )

class Test_openid_logging_to(unittest.TestCase):
    def setUp(self):
        self.log = Mock(name='Logger')

    def capture_logging(self):
        from authopenid.openid_consumer import openid_logging_to
        return openid_logging_to(self.log)

    def test_capture(self):
        with self.capture_logging():
            oidutil.log("foo%s")
            oidutil.log("bar", 3)
        self.assertEqual(self.log.mock_calls, [
            call.warning("%s", "foo%s"),
            call.warning("%s", "bar"),
            ])

    def test_restore_original_logger(self):
        try:
            with self.capture_logging():
                raise DummyException()
        except DummyException:
            pass
        self.assertEqual(oidutil.log.__module__, 'openid.oidutil')

    def test_openid_switched_to_stock_logging(self):
        # XXX: The current git version of python-openid has switched
        # to using the stock logging module.  When that happens, our
        # capture_openid_logging context manager is going to have to
        # be reworked.
        self.assertFalse(
            hasattr(oidutil, 'logging'),
            msg="python-openid appears to have switch to using stock logging")

class TestPickleSession(unittest.TestCase):

    skey = 'skey'

    def setUp(self):
        self.req = Mock(name='Request')
        self.req.session = dict()

    def get_session(self):
        from authopenid.openid_consumer import PickleSession
        return PickleSession(self.req, self.skey)

    def test_persistence(self):
        session = self.get_session()
        session['secret'] = 42
        session = self.get_session()
        self.assertEqual(session['secret'], 42)

    def test_cleanup_when_empty(self):
        session = self.get_session()
        session['secret'] = 42
        self.assertIn(self.skey, self.req.session)
        session.clear()
        self.assertNotIn(self.skey, self.req.session)

    def test_does_not_puke_on_garbage(self):
        self.req.session[self.skey] = (
            "(dp0\nS'id'\np1\nS'44b6b53fc89710f6408b9733'\np2\ns.")
        session = self.get_session()
        self.assertEqual(session, {})


class TestOpenIDConsumer(unittest.TestCase):

    BASE_URL = 'http://example.net/trac'

    def setUp(self):
        from authopenid.openid_consumer import OpenIDConsumer

        self.extension_providers = []
        patcher = patch.object(OpenIDConsumer, 'openid_extension_providers',
                               self.extension_providers)
        self.addCleanup(patcher.stop)
        consumer_class = patcher.start()

        patcher = patch.object(OpenIDConsumer, 'consumer_class')
        self.addCleanup(patcher.stop)
        consumer_class = patcher.start()


        self.oid_consumer = consumer_class.return_value

        self.auth_request = self.oid_consumer.begin.return_value
        self.auth_request.shouldSendRedirect.return_value = False

        self.response = self.oid_consumer.complete.return_value
        self.response.status = SUCCESS
        self.response.endpoint.canonicalID = None
        self.response.identity_url = sentinel.identity

        self.env = EnvironmentStub()


    def get_consumer(self):
        from authopenid.openid_consumer import OpenIDConsumer
        return OpenIDConsumer(self.env)

    def get_request(self):
        req = Mock(name='Request')
        req.session = dict()
        req.authname = 'anonymous'
        req.abs_href = Href(self.BASE_URL)
        def redirect(url, permanent=False):
            raise Redirected(url, permanent)
        req.redirect.side_effect = redirect
        return req

    def consumer_begin(self,
                       identifier='http://example.net/',
                       return_to='http://example.com/'):
        consumer = self.get_consumer()
        req = self.get_request()
        return consumer.begin(req, identifier, return_to)

    def consumer_complete(self):
        consumer = self.get_consumer()
        req = self.get_request()
        return consumer.complete(req)

    def assertRaisesLoginError(self, *args, **kwargs):
        from authopenid.exceptions import LoginError
        return self.assertRaises(LoginError, *args, **kwargs)

    def test_begin_no_identifier(self):
        with self.assertRaisesLoginError():
            self.consumer_begin(identifier=None)

    def test_begin_discovery_failure(self):
        self.oid_consumer.begin.side_effect = DiscoveryFailure('msg', 'status')

        with self.assertRaisesLoginError():
            self.consumer_begin()

    def test_begin_redirect(self):
        self.auth_request.shouldSendRedirect.return_value = True

        with self.assertRaises(Redirected):
            self.consumer_begin()

    def test_begin_autosubmit(self):
        self.auth_request.shouldSendRedirect.return_value = False

        tmpl, data, ctype = self.consumer_begin()
        self.assertEqual(tmpl, 'autosubmitform.html')

    def test_begin_with_extension_providers(self):
        provider = Mock(name='provider')
        self.extension_providers.append(provider)

        self.consumer_begin()
        self.assertEqual(provider.mock_calls, [
            call.add_to_auth_request(ANY, self.auth_request)])

    def test_complete(self):
        self.assertEqual(self.consumer_complete(), (sentinel.identity, {}))

    def test_complete_iname(self):
        self.response.endpoint.canonicalID = sentinel.iname
        self.assertEqual(self.consumer_complete(), (sentinel.iname, {}))

    def test_complete_with_extension_providers(self):
        for ext_data in ({'a': 'b'}, {'c': 'd'}):
            provider = Mock(name='provider')
            provider.parse_response.return_value = ext_data
            self.extension_providers.append(provider)

        identity, extension_data = self.consumer_complete()
        self.assertEqual(extension_data, {'a': 'b', 'c': 'd'})

    def test_complete_failure(self):
        self.response.status = FAILURE
        with self.assertRaises(AuthenticationFailed):
            self.consumer_complete()

    def test_complete_cancelled(self):
        self.response.status = CANCEL
        with self.assertRaises(AuthenticationCancelled):
            self.consumer_complete()

    def test_complete_setup_needed(self):
        self.response.status = SETUP_NEEDED
        with self.assertRaises(SetupNeeded):
            self.consumer_complete()

    def assert_trust_root_equals(self, trust_root):
        consumer = self.get_consumer()
        req = self.get_request()
        self.assertEquals(consumer._get_trust_root(req), trust_root)

    def test_get_trust_root(self):
        self.assert_trust_root_equals('http://example.net/')

    def test_get_trust_root_project(self):
        self.env.config.set('openid', 'absolute_trust_root', False)
        self.assert_trust_root_equals('http://example.net/trac/')



class TestOpenIDConsumerIntegration(unittest.TestCase):
    """ Currently this tests that the IEnvironmentSetupParticipant methods
    work with sqlite.

    XXX: should be fixed to work with other db schemes.
    """

    def setUp(self):
        self.env = EnvironmentStub()
        assert self.env.dburi == 'sqlite::memory:'

    def tearDown(self):
        self.env.global_databasemanager.shutdown()

    def get_consumer(self):
        from authopenid.openid_consumer import OpenIDConsumer
        return OpenIDConsumer(self.env)

    def list_tables(self):
        with self.env.db_query as db:
            return set(table for table, in db("SELECT name FROM sqlite_master"
                                              " WHERE type='table'"))

    def assertOIDTablesExist(self):
        tables = self.list_tables()
        for table in 'oid_associations', 'oid_nonces':
            self.assertIn(table, tables)

    def assertOIDTablesMissing(self):
        tables = self.list_tables()
        for table in 'oid_associations', 'oid_nonces':
            self.assertNotIn(table, tables)

    def test_environment_created(self):
        consumer = self.get_consumer()
        consumer.environment_created()
        self.assertOIDTablesExist()

    def test_environment_upgrade(self):
        consumer = self.get_consumer()
        with self.env.db_transaction as db:
            consumer.upgrade_environment(db)
        self.assertOIDTablesExist()

    def test_environment_needs_upgrade(self):
        consumer = self.get_consumer()

        with self.env.db_query as db:
            self.assertTrue(consumer.environment_needs_upgrade(db))
        self.test_environment_upgrade()
        with self.env.db_query as db:
            self.assertFalse(consumer.environment_needs_upgrade(db))


class DummyException(Exception):
    pass

class Redirected(Exception):
    @property
    def url(self):
        return self.args[0]
