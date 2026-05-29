import unittest

from pc_client import _classify, _extract_queue_position


class TestPokemonCenter(unittest.TestCase):
    def test_queue_detection(self) -> None:
        body = 'queue-it.net waiting room "pos":42000'
        status = _classify(200, body.lower(), "https://queue-it.net/")
        self.assertTrue(status.queue_active)

    def test_position_parse(self) -> None:
        self.assertEqual(_extract_queue_position('"pos":12345'), 12345)


if __name__ == "__main__":
    unittest.main()
