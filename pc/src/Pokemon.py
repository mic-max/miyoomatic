# Pyhon
import base64
import enum
import random
import typing

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Gender(enum.Enum):
    UNKNOWN = 1
    MALE = 2
    FEMALE = 3

    def __str__(self) -> str:
        if self == Gender.MALE:
            return f'{bcolors.OKBLUE}♂{bcolors.ENDC}'
        if self == Gender.FEMALE:
            return f'{bcolors.FAIL}♀{bcolors.ENDC}'
        return f'{bcolors.OKGREEN}⚥{bcolors.ENDC}'

    def file_name_char(self) -> str:
        if self == Gender.MALE:
            return 'm'
        if self == Gender.FEMALE:
            return 'f'
        return 'o'

class Pokemon():
    def __init__(self, pokedex_id: int, name: str, level: typing.Optional[int], gender: typing.Optional[Gender], is_shiny: bool):
        self.pokedex_id = pokedex_id
        self.name = name
        self.level = level
        self.gender = gender
        self.is_shiny = is_shiny

    def __str__(self):
        shiny = " "
        if self.is_shiny:
            shiny = f'{bcolors.WARNING}✧{bcolors.ENDC}'

        lv_str = f'{bcolors.FAIL}LvØØ{bcolors.ENDC}'
        if self.level is not None:
            lv_str = f"Lv{self.level}"

        g_str = f'{bcolors.FAIL}Ø{bcolors.ENDC}'
        if self.gender is not None:
            g_str = str(self.gender)

        return f'{shiny} {self.name} #{self.pokedex_id:03d} {g_str} {lv_str}'

    def file_name(self) -> str:
        lv_str = '00'
        if self.level is not None:
            lv_str = f"{self.level:02d}"

        g_str = '?'
        if self.gender is not None:
            g_str = self.gender.file_name_char()

        rand_id = base64.urlsafe_b64encode(random.randbytes(3)).decode('ascii')
        shiny = 'y' if self.is_shiny else 'n'

        return f'{self.pokedex_id:03d}-{shiny}-{lv_str}-{g_str}-{rand_id}'
