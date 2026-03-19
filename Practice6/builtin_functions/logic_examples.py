from functools import reduce
numbers = [1, 2, 3, 4, 5, 6]
squared = list(map(lambda x: x**2, numbers))
evens = list(filter(lambda x: x % 2 == 0, numbers))
total_sum = reduce(lambda x, y: x + y, numbers)
print(f"Квадраттар: {squared}")
print(f"Жұптар: {evens}")
print(f"Қосынды: {total_sum}")
names = ["Python", "Java", "C++"]
for i, name in enumerate(names, 1):
    print(f"{i}-ші бағдарламалау тілі: {name}")
