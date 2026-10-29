import unittest

from main import DeepSeekBooster


class DeepSeekCacheTests(unittest.TestCase):
    def setUp(self):
        self.booster = DeepSeekBooster()

    def test_depth_is_part_of_cache_key(self):
        self.booster.boost("Frage", depth=1)
        self.booster.boost("Frage", depth=2)

        self.assertEqual(len(self.booster.cache), 2)

    def test_generation_options_are_part_of_cache_key(self):
        base = {
            "language": "de",
            "model": "model-a",
            "max_tokens": 100,
            "system_prompt": "Antworte knapp",
            "response_format": {"type": "json"},
        }
        self.booster.boost("Frage", **base)

        variants = [
            {**base, "language": "en"},
            {**base, "model": "model-b"},
            {**base, "max_tokens": 200},
            {**base, "system_prompt": "Antworte ausführlich"},
            {**base, "response_format": {"type": "text"}},
        ]
        for options in variants:
            self.booster.boost("Frage", **options)

        self.assertEqual(len(self.booster.cache), 6)

    def test_mutating_return_value_does_not_mutate_cache(self):
        first = self.booster.boost("Frage")
        first["reasoning_trace"][0]["note"] = "verändert"

        second = self.booster.boost("Frage")
        self.assertNotEqual(
            second["reasoning_trace"][0]["note"],
            "verändert",
        )


if __name__ == "__main__":
    unittest.main()
