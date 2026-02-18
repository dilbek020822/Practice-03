def print_data(*args, **kwargs):
    print(f"Args: {args}")
    print(f"Kwargs: {kwargs}")

print_data(1, 2, 3, city="Almaty", job="Dev")