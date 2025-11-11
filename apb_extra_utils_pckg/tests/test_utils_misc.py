import os
import unittest
from collections import defaultdict

from apb_extra_utils import misc


class TestUtilsMisc(unittest.TestCase):
    path_logs = os.path.join(os.path.dirname(__file__), "data")

    def setUp(self) -> None:
        pass

    def test_find_key_values(self):
        data = {
            "a": 1,
            "b": {"a": 2, "c": {"a": 3}},
            "d": [{"a": 4}, {"x": 5}],
            "e": {"f": {"g": {"a": 6}}}
        }

        res = defaultdict(list)
        for val, level  in misc.find_key_values(data, 'a'):
            print(f"level={level}: val={val}")
            res[level].append(val)

        self.assertEqual(len(res[0]), 1)
        self.assertEqual(len(res[1]), 1)
        self.assertEqual(len(res[2]), 2)
        self.assertEqual(len(res[3]), 1)


if __name__ == '__main__':
    unittest.main()
