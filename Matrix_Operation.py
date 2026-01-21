def print_matrix(matrix):
    for row in matrix:
        print(row)

def add_matrices(P, Q):
    """Add two matrices."""
    if len(P) != len(Q) or len(P[0]) != len(Q[0]):
        return "Matrices must have the same dimensions for addition."
    result = []
    for i in range(len(P)):
        row = []
        for j in range(len(P[0])):
            row.append(P[i][j] + Q[i][j])
        result.append(row)
    return result

def subtract_matrices(P, Q):
    """Subtract two matrices."""
    if len(P) != len(Q) or len(P[0]) != len(Q[0]):
        return "Matrices must have the same dimensions for subtraction."
    result = []
    for i in range(len(P)):
        row = []
        for j in range(len(P[0])):
            row.append(P[i][j] - Q[i][j])
        result.append(row)
    return result

def multiply_matrices(P, Q):
    """Multiply two matrices."""
    if len(P[0]) != len(Q):
        return "Number of columns in A must be equal to number of rows in B for multiplication."
    result = []
    for i in range(len(P)):
        row = []
        for j in range(len(Q[0])):
            SUM = 0
            for k in range(len(Q)):
                SUM += P[i][k] * Q[k][j]
            row.append(SUM)
        result.append(row)
    return result

def determinant(matrix):
    """Calculate determinant of a 2x2 or 3x3 matrix."""
    if len(matrix) == 2 and len(matrix[0]) == 2:
        return matrix[0][0]*matrix[1][1] - matrix[0][1]*matrix[1][0]
    elif len(matrix) == 3 and len(matrix[0]) == 3:
        a = matrix[0][0]
        b = matrix[0][1]
        c = matrix[0][2]
        d = matrix[1][0]
        e = matrix[1][1]
        f = matrix[1][2]
        g = matrix[2][0]
        h = matrix[2][1]
        i = matrix[2][2]
        return a*(e*i - f*h) - b*(d*i - f*g) + c*(d*h - e*g)
    else:
        return "Determinant calculation only implemented for 2x2 and 3x3 matrices."

def transpose_matrix(matrix):
    """Transpose a matrix."""
    return [list(row) for row in zip(*matrix)]

# Example usage
if __name__ == "__main__":
    A = [[1, 2], [3, 4]]
    B = [[5, 6], [7, 8]]
    print("Matrix A:")
    print_matrix(A)
    print("Matrix B:")
    print_matrix(B)
    print("A + B:")
    print_matrix(add_matrices(A, B))
    print("A - B:")
    print_matrix(subtract_matrices(A, B))
    print("A * B:")
    print_matrix(multiply_matrices(A, B))
    print("Determinant of A:", determinant(A))
    print("Transpose of A:")
    print_matrix(transpose_matrix(A))