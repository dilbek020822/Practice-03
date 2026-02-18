class A:
    def feat_a(self): print("Feat A")

class B:
    def feat_b(self): print("Feat B")

class C(A, B):
    pass

obj = C()
obj.feat_a()
obj.feat_b()