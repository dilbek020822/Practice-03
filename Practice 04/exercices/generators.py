# 1. Squares to N
def sq_gen(n):
    for i in range(n + 1): yield i**2

# 2. Even numbers comma separated
n = int(input("Enter n for even: "))
print(*(i for i in range(n+1) if i%2==0), sep=", ")

# 3. Divisible by 3 and 4
def div_3_4(n):
    for i in range(n + 1):
        if i % 3 == 0 and i % 4 == 0: yield i

# 5. Down to 0
def countdown(n):
    while n >= 0:
        yield n
        n -= 1