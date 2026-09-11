# 파이선연습.py

# 클라스를 정의
class Person:
    # 초기화 메서드
    def __init__(self):
        self.name = "default.name"
    def printInfo(self):
        print("My name is {0}".format(self.name))

# 인스턴스(복사본) 생성
p1 = Person()

# 메서드 호출
p1.printInfo()
