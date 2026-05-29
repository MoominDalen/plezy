import unittest

from discovery.johnlewis_scanner import _extract_pokemon_tcg_urls, _name_from_url


class TestScanner(unittest.TestCase):
    def test_extracts_pokemon_tcg_urls(self) -> None:
        html = '''
        <a href="/pokemon-tcg-trading-card-game-booster/p113617158">x</a>
        <a href="https://www.johnlewis.com/toys/pokemon-tcg-tin/p999">y</a>
        '''
        urls = _extract_pokemon_tcg_urls(html, base="https://www.johnlewis.com/search")
        self.assertTrue(
            any("pokemon-tcg" in u and u.endswith("/p113617158") for u in urls)
        )

    def test_name_from_url(self) -> None:
        url = "https://www.johnlewis.com/pokemon-tcg-booster/p1"
        self.assertIn("Pokemon", _name_from_url(url))


if __name__ == "__main__":
    unittest.main()
