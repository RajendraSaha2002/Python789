import requests


def get_exchange_rate(base_currency, target_currency):
    """
    Fetches the exchange rate from the API.
    """
    # The API endpoint for the latest exchange rates
    url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"

    try:
        # Make a request to the API
        response = requests.get(url)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # Parse the JSON response
        data = response.json()

        # Check if the target currency is in the rates
        if target_currency in data['rates']:
            return data['rates'][target_currency]
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None
    except KeyError:
        print(f"Error: Invalid base currency '{base_currency}'. Please use a valid ISO currency code.")
        return None


def main():
    """
    Main function to run the currency converter.
    """
    print("--- Currency Converter ---")

    # Get user input
    base_currency = input("Enter the base currency (e.g., USD, EUR, JPY): ").upper()
    target_currency = input("Enter the target currency (e.g., USD, EUR, JPY): ").upper()

    while True:
        try:
            amount_str = input(f"Enter the amount in {base_currency}: ")
            amount = float(amount_str)
            break
        except ValueError:
            print("Invalid input. Please enter a valid number for the amount.")

    # Get the exchange rate
    print(f"\nFetching exchange rate for {base_currency} to {target_currency}...")
    rate = get_exchange_rate(base_currency, target_currency)

    if rate is not None:
        # Calculate the converted amount
        converted_amount = amount * rate

        # Display the result
        print("\n--- Result ---")
        print(f"{amount} {base_currency} is equal to {converted_amount:.2f} {target_currency}")
        print(f"Current exchange rate: 1 {base_currency} = {rate} {target_currency}")
    else:
        print(
            f"\nCould not get the exchange rate for {target_currency}. Please check the currency codes and try again.")


if __name__ == "__main__":
    main()