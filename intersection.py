from math import pi
import mathutils
from . import algebra

def intersect_2d(pa, pb, pc, pd):
    """Find the intersection point of the lines AB and DC (2 dimensions)."""
    # Helper vectors
    ad = pd - pa
    ab = pb - pa
    cd = pd - pc
    # Solve linear system of equations s * ab + t * cd = ad
    tmp = algebra.solve_linear_system_2d(ab[0], cd[0], ad[0], ab[1], cd[1], ad[1])
    # Check for parallel lines
    if not tmp:
        return None
    s, t = tmp
    # Return the intersection point
    return pa + s * ab