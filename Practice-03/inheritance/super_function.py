class Parent:
    def __init__(self, name):
        self.name = name

class Child(Parent):
    def __init__(self, name, school):
        super().__init__(name)
        self.school = school

ch = Child("Almas", "School #1")
print(ch.name, ch.school)