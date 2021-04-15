import tvfile
import requests
import json

from requests.exceptions import Timeout
from requests import Response

from unittest import TestCase
from unittest.mock import Mock, patch

# Run tests from project directory with `python -m unittest tests`


def make_response(http_status_code):
    r = requests.Response()
    r.status_code = http_status_code
    return r

def send_episodes(page, dump_str=False):
    filepath = "tests/data/seinfeld-episodes-page-{}.json".format(str(page))
    with open(filepath, 'r') as fh:
        data = json.load(fh)
    if dump_str:
        return json.dumps(data)
    else:
        return data


class TvDataTests(TestCase):

    @patch('tvfile.try_query')
    def test_get_all_episodes(self, mock_try_query):
        """get_all_episodes returns both pages of test data and 
        concatenates the episodes into one list"""
        ep_list_one = send_episodes('1')
        ep_list_two = send_episodes('2')
        num_episodes = len(ep_list_one['data']) + len(ep_list_two['data'])
        response_mock = Mock(name='Mocked response from try_query')
        response_mock.json.side_effect = [ep_list_one, ep_list_two]
        mock_try_query.return_value = response_mock
        all_episodes_json = tvfile.get_all_episodes('79169')
        mock_try_query.assert_called()
        self.assertIsInstance(all_episodes_json, list)
        self.assertEqual(num_episodes, len(all_episodes_json))
        self.assertIn('episodeName', all_episodes_json[0])

    @patch('tvfile.requests')
    def test_get_episodes_success(self, mock_requests):
        """get_episodes returns an unmodified response object"""
        response_mock = Mock(name='Mocked response from the tvdb api')
        response_mock.status_code = 200
        response_mock.json.return_value = send_episodes('1')

        mock_requests.get.return_value = response_mock
        r = tvfile.get_episodes('79169')
        episodes_json = send_episodes('1')
        self.assertEqual(r.json(), episodes_json)
        self.assertIn('data', episodes_json)


class TryQueryTests(TestCase):

    tvfile.get_token = Mock(return_value=None, name='Mock Get Token')

    def test_try_query_success(self):
        """A response from try_query is returned with a successful status code on the first try"""
        http_code = requests.codes.ok
        query_func = make_response
        r = tvfile.try_query(query_func, http_code)
        self.assertEqual(r.status_code, http_code)

    def test_try_query_bad(self):
        """404 not found status is reported every try, and no response from try_query is returned"""
        http_code = requests.codes.not_found
        query_func = make_response
        r = tvfile.try_query(query_func, http_code)
        self.assertIsNone(r)

    def test_try_query_unauthorized(self):
        """Every query try gets status code 401 authorized, no response from try_query is returned"""
        http_code = requests.codes.unauthorized
        query_func = make_response
        r = tvfile.try_query(query_func, http_code)
        tvfile.get_token.assert_called()
        self.assertIsNone(r)

    def test_try_query_fail_then_success(self):
        """Query succeeds on second attempt and try_query returns a matching response"""
        response_1 = make_response(requests.codes.not_found)
        response_2 = make_response(requests.codes.ok)
        query_func = Mock(side_effect=[response_1, response_2])
        r = tvfile.try_query(query_func)
        self.assertEqual(query_func.call_count, 2)
        self.assertEqual(r.status_code, response_2.status_code)


if __name__ == "__main__":
    unittest.main()
