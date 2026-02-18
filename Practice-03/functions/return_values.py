def get_min_max(numbers):
    return min(numbers), max(numbers)

mn, mx = get_min_max([10, 2, 45, 1])
print(f"Min: {mn}, Max: {mx}")