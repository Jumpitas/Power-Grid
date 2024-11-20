import random

while True:
    c = 1
    while c!=1:
        x = random.randint(1, 100)
        if x==27:
            print(c)
            break
        c+=1
