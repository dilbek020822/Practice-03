import math
# 1. Degree to Radian
deg = 15
print(f"Radian: {math.radians(deg):.6f}")
# 2. Trapezoid
h, b1, b2 = 5, 5, 6
print(f"Trapezoid Area: {(b1+b2)*h/2}")
# 3. Polygon
n, s = 4, 25
print(f"Polygon Area: {(n * s**2) / (4 * math.tan(math.pi / n)):.0f}")
# 4. Parallelogram
print(f"Parallelogram Area: {5 * 6}")