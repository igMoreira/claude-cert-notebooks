"""
Module for calculating pi to specific decimal places.
"""

from decimal import Decimal, getcontext


def calculate_pi_to_5th_digit():
    """
    Calculate pi to the 5th decimal place using the Machin formula.
    
    The Machin formula: pi/4 = 4*arctan(1/5) - arctan(1/239)
    
    Returns:
        float: Pi calculated to the 5th decimal place (3.14159)
    """
    # Set precision high enough for accurate calculation
    getcontext().prec = 50
    
    # Use Machin formula: pi/4 = 4*arctan(1/5) - arctan(1/239)
    # This converges quickly and is efficient
    
    def arctan(x, num_terms=100):
        """Calculate arctan using Taylor series."""
        x = Decimal(x)
        result = Decimal(0)
        for n in range(num_terms):
            term = ((-1) ** n) * (x ** (2 * n + 1)) / (2 * n + 1)
            result += term
        return result
    
    # Calculate pi using Machin formula
    one = Decimal(1)
    five = Decimal(5)
    two_three_nine = Decimal(239)
    
    pi = 4 * (4 * arctan(one / five) - arctan(one / two_three_nine))
    
    # Round to 5th decimal place
    pi_rounded = float(round(pi, 5))
    
    return pi_rounded


if __name__ == "__main__":
    result = calculate_pi_to_5th_digit()
    print(f"Pi calculated to 5th digit: {result}")