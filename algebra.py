def solve_linear_system_2d(a, b, c, d, e, f):
    """Solves the system of equations a*x + b*y = c, d*x + e*y = e using Gaussian Elimination (for numerical stability)."""
    # Pivoting (to obtain stability)
    if abs(d) > abs(a):
        a, b, c, d, e, f = (d, e, f, a, b, c)
    # Check for singularity
    if a == 0:
        return None
    tmp = e - d * b / a
    if tmp == 0:
        return None
    # This is final answer of the gaussian elimination
    y = (f - d * c / a) / tmp
    x = (c - b * y) / a
    return (x, y)
