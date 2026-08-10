"""
Test suite for the pi calculation function.
"""

import unittest
from main import calculate_pi_to_5th_digit


class TestPiCalculation(unittest.TestCase):
    """Test cases for calculate_pi_to_5th_digit function."""
    
    def test_pi_returns_float(self):
        """Test that the function returns a float."""
        result = calculate_pi_to_5th_digit()
        self.assertIsInstance(result, float)
    
    def test_pi_correct_value(self):
        """Test that pi is calculated correctly to 5 decimal places."""
        result = calculate_pi_to_5th_digit()
        expected = 3.14159
        self.assertEqual(result, expected)
    
    def test_pi_in_valid_range(self):
        """Test that the calculated pi is in the valid range."""
        result = calculate_pi_to_5th_digit()
        # Pi should be between 3 and 4
        self.assertGreater(result, 3)
        self.assertLess(result, 4)
    
    def test_pi_greater_than_314(self):
        """Test that pi is greater than 3.14."""
        result = calculate_pi_to_5th_digit()
        self.assertGreater(result, 3.14)
    
    def test_pi_less_than_3142(self):
        """Test that pi is less than 3.142."""
        result = calculate_pi_to_5th_digit()
        self.assertLess(result, 3.142)
    
    def test_pi_5_decimal_places(self):
        """Test that the result has at most 5 decimal places."""
        result = calculate_pi_to_5th_digit()
        # Multiply by 10^5 and check if it's an integer (accounting for floating point precision)
        scaled = result * 100000
        # The scaled value should be very close to an integer
        self.assertAlmostEqual(scaled, round(scaled), places=5)
    
    def test_consistency(self):
        """Test that multiple calls return the same value."""
        result1 = calculate_pi_to_5th_digit()
        result2 = calculate_pi_to_5th_digit()
        result3 = calculate_pi_to_5th_digit()
        
        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)
    
    def test_pi_approximation_accuracy(self):
        """Test that pi is accurate to within 0.00001 of the expected value."""
        result = calculate_pi_to_5th_digit()
        expected = 3.14159
        self.assertAlmostEqual(result, expected, places=5)


if __name__ == "__main__":
    unittest.main()
