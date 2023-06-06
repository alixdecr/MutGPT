from colorama import init, Fore, Style


class Logger:


    def __init__(self):

        # initialize colorama colors on Windows machines
        init()

        self.colorDict = {"red": Fore.RED, "blue": Fore.BLUE, "green": Fore.GREEN, "white": Fore.WHITE, "purple": Fore.MAGENTA, "yellow": Fore.YELLOW}


    def logMessage(self, message, type, color, newLine=False, extra=""):

        # if parameter color is valid, surround message with that color
        if color in self.colorDict:
            coloredMessage = self.colorDict[color] + message + Style.RESET_ALL
        else:
            coloredMessage = message

        # if need for a new line, add it
        if newLine:
            line = "\n"
        else:
            line = ""

        # if extra text is specified, add it after ':'
        if extra != "":
            coloredMessage += f": {extra}"

        if type == "title":
            print(f"{line}--- {coloredMessage} ---")

        elif type == "bullet":
            print(f"{line} - {coloredMessage}")

        elif type == "arrow":
            print(f"{line} -> {coloredMessage}")

        else:
            print(f"{line}{coloredMessage}")
