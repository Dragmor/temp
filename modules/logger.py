import colorama
from colorama import Fore, Back, Style
from datetime import datetime

colorama.init(autoreset=True)


def debug(text):
    print(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.CYAN + "[DEBUG]",
        ">",
        Style.BRIGHT + Fore.CYAN + text
    )


def info(text):
    print(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.GREEN + "[INFO]",
        ">",
        Style.BRIGHT + Fore.GREEN + text
    )


def error(text):
    print(
        Style.BRIGHT + datetime.now().strftime("%d-%m-%Y : %H:%M:%S"),
        ">",
        Fore.RED + "[ERROR]",
        ">",
        Style.BRIGHT + Fore.RED + text
    )
