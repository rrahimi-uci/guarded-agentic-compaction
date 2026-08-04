import typing
from typing import List
from typing import Tuple
from math import gcd
import math
from math import factorial
from math import comb
from typing import Union


def permutation(n: int, r: int) -> int:
    """
    Calculate the number of permutations of n items taken r at a time
    :param n: Total number of items
    :type n: int
    :param r: Number of items being arranged
    :type r: int
    :return: Number of permutations
    :rtype: int
    """
    return factorial(n) // factorial(n - r)


def subtract(arg_0: int or float, arg_1: int or float) -> int or float:
    """
    Subtract two numbers
    :param arg_0: The first number
    :param arg_1: The second number
    :return: The subtraction result
    """
    return arg_0 - arg_1


def power(base: typing.Union[int, float], exponent: typing.Union[int, float]) -> typing.Union[int, float]:
    """
    Raise a number to a power
    :param base: The base number
    :param exponent: The exponent number
    :return: the power result
    """
    return base ** exponent


def sqrt(num: int) -> int:
    """
    Calculate the square root of a non-negative number.
    Args:
    num (int): The input number
    Returns:
    int: the square root of the provided number
    """
    return math.isqrt(num)


def volume_cylinder(radius: float, height: float) -> float:
    """
    Calculate the volume of a cylinder
    :param radius: Radius of the base of the cylinder
    :param height: Height of the cylinder
    :return: Volume of the cylinder
    """
    return math.pi * radius ** 2 * height


def max_number(numbers: List[float]) -> float:
    """
    Find the maximum value among the given numbers
    :param numbers: A list of numbers
    :type numbers: List[float]
    :return: Maximum value
    :rtype: float
    """
    return max(numbers)


def multiply(arg_0: int or float, arg_1: int or float) -> int or float:
    """
    Multiplies two numbers
    :param arg_0: The first number
    :param arg_1: The second number
    :return: The multiplication result
    """
    return arg_0 * arg_1


def surface_sphere(radius: float) -> float:
    """
    Calculate the surface area of a sphere
    Args:
    radius (float): Radius of the sphere
    Returns:
    float: Surface area of the sphere
    """
    return 4 * math.pi * radius ** 2


def rectangle_area(length: float, width: float) -> float:
    """
    Calculate the area of a rectangle given its length and width
    :param length: rectangle length
    :param width: rectangle width
    :return: the rectangle area
    """
    return length * width


def remainder(a: typing.Union[int, float], b: typing.Union[int, float]) -> typing.Union[int, float]:
    """
    Calculate the remainder of a divided by b
    :param a: first number
    :param b: second number
    :return: the remainder
    """
    return a % b


def square_edge_by_area(area: float) -> float:
    """
    Calculate the edge length of a square given its area
    Args:
    area (float): Area of the square
    Returns:
    float: Edge length of the square
    """
    return math.sqrt(area)


def divide(arg_0: int or float, arg_1: int or float) -> int or float:
    """
    Divides two numbers.
    :param arg_0: The first number
    :type arg_0: int or float
    :param arg_1: The second number
    :type arg_1: int or float
    :return: The division result
    :rtype: int or float
    """
    return arg_0 / arg_1


def add(arg_0: int or float, arg_1: int or float) -> int or float:
    """
    Adds two numbers.
    Args:
    arg_0 (int or float): The first number.
    arg_1 (int or float): The second number.
    Returns:
    result (int or float): The addition result.
    """
    return arg_0 + arg_1


def circle_area(radius):
    """
    Calculate the area of a circle given its radius
    Args:
    radius (int or float): The circle radius
    Returns:
    int or float: the circle area
    """
    return math.pi * radius ** 2


def triangle_area(base: float, height: float) -> float:
    """
    Calculate the area of a triangle given base and height
    :param base: Length of the base of the triangle
    :param height: Height of the triangle
    :return: Area of the triangle
    """
    return 0.5 * base * height


def circumface(radius: float) -> float:
    """
    Calculate the circumference of a circle
    Args:
    radius (float): Radius of the circle
    Returns:
    float: Circumference of the circle
    """
    return 2 * math.pi * radius


def volume_sphere(radius: float) -> float:
    """
    Calculate the volume of a sphere
    Args:
    radius (float): Radius of the sphere
    Returns:
    float: Volume of the sphere
    """
    return (4/3) * math.pi * radius**3


def square_perimeter(side_length: Union[int, float]) -> Union[int, float]:
    """
    Calculate the perimeter of a square given its side length
    :param side_length: side length
    :type side_length: int or float
    :return: the square perimeter
    :rtype: int or float
    """
    return 4 * side_length


def cube_edge_by_volume(volume: float) -> float:
    """
    Calculate the edge length of a cube given its volume.
    :param volume: Volume of the cube
    :type volume: float
    :return: Edge length of the cube
    :rtype: float
    """
    return math.pow(volume, 1/3)


def floor(x: float) -> int:
    """
    Return the largest integer less than or equal to x.
    Args:
    x (int): The input number
    Returns:
    int: the flooring result
    """
    return math.floor(x)


def diagonal(length: float, width: float) -> float:
    """
    Calculate the length of the diagonal of a rectangle
    :param length: Length of the rectangle
    :param width: Width of the rectangle
    :return: Length of the diagonal
    """
    return math.sqrt(length**2 + width**2)


def choose(n: int, r: int) -> int:
    """
    Calculate the number of ways to choose r items from n items without repetition and without order.
    :param n: Total number of items
    :type n: int
    :param r: Number of items being chosen
    :type r: int
    :return: Number of combinations
    :rtype: int
    """
    return comb(n, r)


def lcm(a: int or float, b: int or float) -> int or float:
    """
    Calculate the least common multiple of two numbers
    :param a: first number
    :param b: second number
    :return: the least common multiple
    """
    return abs(a*b) // gcd(a, b)


def negate(number):
    """
    Return the negation of a number
    Args:
    number (int or float): The number to inverse
    Returns:
    result (int or float): The inverse result
    """
    return -number


def rectangle_perimeter(length: float, width: float) -> float:
    """
    Calculate the perimeter of a rectangle
    :param length: rectangle length
    :param width: rectangle width
    :return: the rectangle perimeter
    """
    return 2 * (length + width)


def min_number(numbers: List[float]) -> float:
    """
    Find the minimum value among the given numbers
    :param numbers: A list of numbers
    :type numbers: List[float]
    :return: Minimum value
    :rtype: float
    """
    return min(numbers)


def volume_cone(radius: float, height: float) -> float:
    """
    Calculate the volume of a cone
    :param radius: Radius of the base of the cone
    :type radius: float
    :param height: Height of the cone
    :type height: float
    :return: Volume of the cone
    :rtype: float
    """
    return (1/3) * math.pi * radius**2 * height


def square_area(side: int or float) -> int or float:
    """
    Calculate the area of a square given its side
    Args:
    side (int or float): The square side
    Returns:
    result (int or float): the square area
    """
    return side * side


def factorial(n: int) -> int:
    """
    Calculate the factorial of a non-negative integer
    Args:
    n (int): The input number
    Returns:
    int: the factorial result
    """
    if n < 0:
        raise ValueError("Input number must be a non-negative integer")
    elif n == 0:
        return 1
    else:
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result


def rhombus_area(diagonal1: float, diagonal2: float) -> float:
    """
    Calculate the area of a rhombus
    Args:
    diagonal1 (float): Length of the first diagonal
    diagonal2 (float): Length of the second diagonal
    Returns:
    float: Area of the rhombus
    """
    return 0.5 * diagonal1 * diagonal2


def log(x: float, base: float = math.e) -> int:
    """
    Calculate the logarithm of x with the given base (default is natural log)
    Args:
    x (int or float): The input number
    base (int or float, optional): The base. Defaults to math.e.
    Returns:
    int: logarithm of provided number with the given base
    """
    return int(math.log(x, base))


def gcd(arg_0: int or float, arg_1: int or float) -> int or float:
    """
    Calculate the Greatest Common Divisor (GCD) of two numbers.
    :param arg_0: first number
    :param arg_1: second number
    :return: Greatest Common Divisor
    """
    return math.gcd(int(arg_0), int(arg_1))


def reminder(a: typing.Union[int, float], b: typing.Union[int, float]) -> typing.Union[int, float]:
    """
    Calculate the remainder of a divided by b
    :param a: first number
    :param b: second number
    :return: the remainder
    """
    return a % b


def speed(distance: Union[int, float], time: Union[int, float]) -> Union[int, float]:
    """Calculate speed given distance and time.
    Args:
    distance (int or float): The distance traveled.
    time (int or float): The time taken to travel the distance.
    Returns:
    int or float: The speed.
    """
    return distance / time


def square_edge_by_perimeter(perimeter: float) -> Tuple[float]:
    """
    Calculate the edge length of a square given its perimeter
    :param perimeter: Perimeter of the square
    :type perimeter: float
    :return: Edge length of the square
    :rtype: float
    """
    edge_length = perimeter / 4
    return edge_length


def volume_cube(side_length: float) -> float:
    """
    Calculate the volume of a cube.
    Args:
    side_length (float): Length of a side of the cube.
    Returns:
    float: Volume of the cube.
    """
    return side_length ** 3


def negate_prob(prob: Union[float, int]) -> float:
    """
    Calculate the probability of an event not occurring
    Args:
    prob (Union[float, int]): Probability of the event occurring
    Returns:
    float: Probability of the event not occurring
    """
    return 1 - prob


def inverse(number: Union[int, float]) -> Union[int, float]:
    """
    Return the inverse (reciprocal) of a number
    :param number: The number to inverse
    :type number: int or float
    :return: The inverse result
    :rtype: int or float
    """
    return 1 / number


def surface_cylinder(radius: float, height: float) -> float:
    """
    Calculate the surface area of a cylinder
    Args:
    radius (float): Radius of the base of the cylinder
    height (float): Height of the cylinder
    Returns:
    float: Surface area of the cylinder
    """
    surface_area = 2 * math.pi * radius * (radius + height)
    return surface_area


def surface_cube(side_length: float) -> float:
    """
    Calculate the surface area of a cube.
    :param side_length: Length of a side of the cube
    :type side_length: float
    :return: Surface area of the cube
    :rtype: float
    """
    return 6 * side_length ** 2
