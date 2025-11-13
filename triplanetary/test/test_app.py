from unittest import mock, TestCase

import app
from chalicelib import env_util

env = {'S3_USERS_BUCKET': 'triplanetary-users-stage',
       'stage': 'stage'}


class TestApp(TestCase):
    def test_dummy(self):
        self.assertEqual(None, None)


if __name__ == '__main__':
    unittest.main()
