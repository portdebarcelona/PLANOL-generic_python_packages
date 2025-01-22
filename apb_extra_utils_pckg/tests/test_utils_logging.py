import os
import unittest
from logging import DEBUG, ERROR, INFO

from apb_extra_utils import misc
from apb_extra_utils.utils_logging import get_root_logger, get_file_logger, get_base_logger, logger_path_logs


class TestUtilsLogging(unittest.TestCase):
    path_logs = os.path.join(os.path.dirname(__file__), "data")

    def setUp(self) -> None:
        pass

    def test_root_logger(self):
        logger = get_root_logger()
        self.assertIsNotNone(logger)

    def test_base_logger(self):
        """ Create a test for function get_base_logger"""
        get_root_logger().setLevel(DEBUG)
        logger = get_base_logger(level=INFO)
        self.assertEqual(misc.caller_name(0), logger.name)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        logger.critical("critical")
        nom_base_log = 'test_base_logger'

        logger2 = get_base_logger(nom_base_log, level=DEBUG)
        self.assertEqual(nom_base_log, logger2.name)
        logger2.debug("debug")
        logger2.info("info")
        logger2.warning("warning")
        logger2.error("error")
        logger2.critical("critical")
        self.assertTrue(logger2.hasHandlers())

    def test_file_logger(self):
        logger = get_file_logger('test_file_logger', dir_log=self.path_logs)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        logger.critical("critical")
        self.assertEqual(len(logger_path_logs(logger)), 2)  # REPORT AND PROBLEMS

        logger = get_file_logger('test_file_logger_2', INFO, self.path_logs, separate_reports=False)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        logger.critical("critical")
        self.assertEqual(len(logger_path_logs(logger)), 1)  # Only one log file

        logger = get_file_logger('test_file_logger_3', ERROR, self.path_logs, sufix_date=False, separate_reports=False)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        logger.critical("critical")
        with open(logger_path_logs(logger)[0], 'r') as f:
            self.assertEqual(len(f.readlines()), 2)  # Only 2 lines written from level ERROR


if __name__ == '__main__':
    unittest.main()
