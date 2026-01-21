import math

def area_circle(radius):
    """Calculate the area of a circle."""
    return math.pi * radius ** 2

def area_rectangle(length, width):
    """Calculate the area of a rectangle."""
    return length * width

def area_triangle(base, height):
    """Calculate the area of a triangle."""
    return 0.5 * base * height

def volume_cube(side):
    """Calculate the volume of a cube."""
    return side ** 3

def volume_sphere(radius):
    """Calculate the volume of a sphere."""
    return (4/3) * math.pi * radius ** 3

def volume_cylinder(radius, height):
    """Calculate the volume of a cylinder."""
    return math.pi * radius ** 2 * height

# Example usage
if __name__ == "__main__":
    print("Area and Volume Calculator")
    print("1. Area of Circle")
    print("2. Area of Rectangle")
    print("3. Area of Triangle")
    print("4. Volume of Cube")
    print("5. Volume of Sphere")
    print("6. Volume of Cylinder")
    choice = input("Enter your choice (1-6): ")

    if choice == '1':
        r = float(input("Enter radius: "))
        print("Area of Circle:", area_circle(r))
    elif choice == '2':
        l = float(input("Enter length: "))
        w = float(input("Enter width: "))
        print("Area of Rectangle:", area_rectangle(l, w))
    elif choice == '3':
        b = float(input("Enter base: "))
        h = float(input("Enter height: "))
        print("Area of Triangle:", area_triangle(b, h))
    elif choice == '4':
        s = float(input("Enter side: "))
        print("Volume of Cube:", volume_cube(s))
    elif choice == '5':
        r = float(input("Enter radius: "))
        print("Volume of Sphere:", volume_sphere(r))
    elif choice == '6':
        r = float(input("Enter radius: "))
        h = float(input("Enter height: "))
        print("Volume of Cylinder:", volume_cylinder(r, h))
    else:
        print("Invalid choice.")