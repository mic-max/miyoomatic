# Python
import typing

def get_pokemon_name(exp_names: typing.List[str]) -> str:
    for i, name in enumerate(exp_names, start=1):
        print(f"{i}. {name}")
    result = 0
    while result not in [str(i) for i in range(1, 1 + len(exp_names))]:
        result = input("Who's that Pokemon? ")

    return exp_names[int(result) - 1]

# TODO: trim and strip user input

def confirm_shiny_result() -> bool:
    print("1. Regular")
    print("9. Shiny")
    result = ""
    while result != "1" and result != "9":
        result = input("Confirm the palette: ")
    return result == '9'