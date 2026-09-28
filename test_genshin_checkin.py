import unittest
from unittest.mock import Mock, patch
import requests
import genshin_checkin as bot


class ResinTests(unittest.TestCase):
    def response(self, payload):
        return Mock(status_code=200, json=Mock(return_value=payload))

    @patch.object(bot.requests, 'get')
    def test_request_and_recovery_from_api(self, get):
        get.return_value = self.response({'retcode': 0, 'data': {
            'current_resin': 120, 'max_resin': 200, 'resin_recovery_time': '123'}})
        data = bot.get_resin_info('800000001', 'os_asia', 'fake=cookie', 'test')
        kwargs = get.call_args.kwargs
        self.assertEqual(kwargs['params'], {'role_id': '800000001', 'server': 'os_asia'})
        self.assertIn('DS', kwargs['headers'])
        report = bot.build_report('test', {}, [], None, None, True, data)
        self.assertIn('120/200', report)
        self.assertIn('In 0h 3m', report)

    @patch.object(bot.requests, 'get')
    def test_errors_are_actionable(self, get):
        for code, expected in [(-100, 'cookie'), (10102, 'Real-Time Notes'),
                               (1034, 'verification'), (999, 'retcode 999')]:
            with self.subTest(code=code):
                get.return_value = self.response({'retcode': code})
                with self.assertRaisesRegex(bot.ResinError, expected):
                    bot.get_resin_info('800000001', 'os_asia', 'fake=cookie', 'test')

    @patch.object(bot.requests, 'get')
    def test_transport_and_malformed_response(self, get):
        get.side_effect = requests.Timeout()
        with self.assertRaisesRegex(bot.ResinError, 'Cannot reach'):
            bot.get_resin_info('800000001', 'os_asia', 'fake=cookie', 'test')
        get.side_effect = None
        for payload in [None, {'retcode': 0, 'data': {}}, {'retcode': 0, 'data': None}]:
            get.return_value = self.response(payload)
            with self.assertRaisesRegex(bot.ResinError, 'unexpected'):
                bot.get_resin_info('800000001', 'os_asia', 'fake=cookie', 'test')

    def test_full_resin_and_html_error(self):
        report = bot.build_report('test', {}, [], None, None, True,
                                 {'current_resin': 200, 'max_resin': 200, 'resin_recovery_time': 0})
        self.assertIn('Resin is full!', report)
        report = bot.build_report('test', {}, [], None, None, True, resin_error='<unavailable>')
        self.assertIn('&lt;unavailable&gt;', report)

    def test_resin_failure_preserves_checkin_report(self):
        with patch.object(bot, 'get_sign_info', return_value={'is_sign': False, 'total_sign_day': 0}), \
             patch.object(bot, 'get_reward_list', return_value=[]), \
             patch.object(bot, 'do_sign', return_value={'retcode': 0}) as sign, \
             patch.object(bot, 'get_resin_info', side_effect=bot.ResinError('Enable Real-Time Notes')), \
             patch.object(bot, 'send_telegram') as send:
            self.assertTrue(bot.process_user({'name': 'test', 'cookie': 'fake'}, 'test'))
            sign.assert_called_once()
            self.assertIn('Check-in successful', send.call_args.args[2])
            self.assertIn('Enable Real-Time Notes', send.call_args.args[2])


if __name__ == '__main__':
    unittest.main()
