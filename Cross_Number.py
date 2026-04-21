n=5
for i in range(n):
    for j in range(n):
        print(i if i==j or i+j==n-1 else ' ', end='')
        print()