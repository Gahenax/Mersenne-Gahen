import unittest
import sys
import os

# Add project root to sys.path to import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mersenne.ghost_hunter_lab import permute_blocks

class TestGhostHunter(unittest.TestCase):
    def test_permute_blocks_happy_path(self):
        data = b"abcdefgh"
        block_size = 2
        seed = 42
        result = permute_blocks(data, block_size, seed)
        self.assertEqual(len(result), len(data))
        # Verify all blocks are present
        original_blocks = [data[i:i+block_size] for i in range(0, len(data), block_size)]
        result_blocks = [result[i:i+block_size] for i in range(0, len(result), block_size)]
        self.assertEqual(sorted(original_blocks), sorted(result_blocks))

    def test_permute_blocks_len_equal_block_size(self):
        data = b"abcd"
        block_size = 4
        seed = 42
        result = permute_blocks(data, block_size, seed)
        self.assertEqual(result, data)

    def test_permute_blocks_len_less_than_block_size(self):
        data = b"abc"
        block_size = 4
        seed = 42
        result = permute_blocks(data, block_size, seed)
        self.assertEqual(result, data)

    def test_permute_blocks_not_multiple(self):
        data = b"abcdef"
        block_size = 4
        seed = 42
        # blocks: [b"abcd", b"ef"]
        result = permute_blocks(data, block_size, seed)
        self.assertEqual(len(result), len(data))

        # Possible outcomes of shuffle([b"abcd", b"ef"])
        possible = [b"abcdef", b"efabcd"]
        self.assertIn(result, possible)

    def test_permute_blocks_invalid_block_size(self):
        with self.assertRaises(ValueError):
            permute_blocks(b"abc", 0, 42)
        with self.assertRaises(ValueError):
            permute_blocks(b"abc", -1, 42)

    def test_permute_blocks_determinism(self):
        data = b"this is a test for determinism"
        block_size = 4
        seed = 123
        res1 = permute_blocks(data, block_size, seed)
        res2 = permute_blocks(data, block_size, seed)
        self.assertEqual(res1, res2)

    def test_permute_blocks_different_seeds(self):
        data = b"this is a test for randomness" * 10
        block_size = 4
        res1 = permute_blocks(data, block_size, 1)
        res2 = permute_blocks(data, block_size, 2)
        self.assertNotEqual(res1, res2)

if __name__ == '__main__':
    unittest.main()
