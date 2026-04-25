from geopy.distance import geodesic

def calculate_distance(loc1, loc2, city1, city2):
    try:
        distance = geodesic(loc1, loc2)

        print("\n📍 Distance Details")
        print("-" * 30)
        print(f"From  : {city1}")
        print(f"To    : {city2}")
        print(f"KM    : {distance.km:.2f}")
        print(f"Miles : {distance.miles:.2f}")

    except Exception as e:
        print("❌ Error:", e)


def main():
    print("🌍 Distance Calculator Between Two Cities\n")

    city1 = input("Enter City 1 name: ")
    lat1 = float(input("Enter Latitude of City 1: "))
    lon1 = float(input("Enter Longitude of City 1: "))

    city2 = input("\nEnter City 2 name: ")
    lat2 = float(input("Enter Latitude of City 2: "))
    lon2 = float(input("Enter Longitude of City 2: "))

    loc1 = (lat1, lon1)
    loc2 = (lat2, lon2)

    calculate_distance(loc1, loc2, city1, city2)


if __name__ == "__main__":
    main()