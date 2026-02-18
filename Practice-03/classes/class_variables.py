class Circle:
    pi = 3.14 # Class variable

    def __init__(self, radius):
        self.radius = radius # Instance variable

c1 = Circle(5)
print(c1.pi, c1.radius)