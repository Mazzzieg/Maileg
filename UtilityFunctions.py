from datetime import datetime, timedelta
from config import LANGUAGE


class UtilityFunctions:
    """
    A collection of utility functions to facilitate common tasks such as formatting data sizes, parsing dates, and handling string representations of dates and times.

    This class is designed to handle various common operations that are not specific to the business logic of applications but are used multiple times across different parts of an application. These include converting data sizes to a human-readable format, extracting the day of the week from a date, and formatting dates from email headers.

    Attributes
    ----------
    logger : logging.Logger
        The logger instance used to log messages and operations performed by the utility functions.

    Methods
    -------
    __init__(self, logger)
        Constructs all the necessary attributes for the UtilityFunctions object.
    get_size_format(self, b, factor: int = 1024, suffix: str = "B") -> str
        Converts a size in bytes to a human-readable string in a format like KB, MB, GB, etc.
    day_of_a_week(self, date_time: str) -> str
        Determines the day of the week from a given date string and returns its Polish name.
    format_date(self, value: str) -> str
        Converts a date string from an email header to a more readable date format.
    """

    def __init__(self, logger):
        """
        Initializes the UtilityFunctions class with a logger instance.

        Parameters
        ----------
        logger : logging.Logger
            The logger instance to be used for logging messages and operations.
        """
        self.logger = logger

    def get_size_format(self, b, factor: int = 1024, suffix: str = "B") -> str:
        """
        Scale bytes to a human-readable format (e.g., kilobytes, megabytes).

        Args:
            b (int): The number of bytes to format.
            factor (int): The factor for scaling (default is 1024).
            suffix (str): The suffix for the format (default is "B").

        Returns:
            str: The formatted size as a string.
        """
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            if b < factor:
                return f"{b:.2f}{unit}{suffix}"
            b /= factor
        return f"{b:.2f}Y{suffix}"

    def day_of_a_week(self, date_time: str) -> str:
        """
        Returns the day of the week for a given date and time from a Gmail Calendar, in Polish.

        This method takes a date and time string from the Gmail Calendar, parses it to extract the date,
        and determines the day of the week as a string in Polish. The input date string should be in the
        format 'YYYY-MM-DDTHH:MM:SSZ'. The method is designed with error
        handling to manage scenarios where the date string is improperly formatted or contains invalid
        date values.

        Args:
            date_time (str): The date and time string from Gmail Calendar, expected in the
                            'YYYY-MM-DDTHH:MM:SSZ' format.

        Returns:
            str: The day of the week in language chosen in config.
        """
        try:
            date_parsed = datetime.strptime(date_time.split("T")[0], "%Y-%m-%d")
            day_name = date_parsed.strftime('%A')
            return self.translator(day_name.lower(), LANGUAGE).capitalize()
        except ValueError as e:
            self.logger.error("Error parsing date string %s: %s", date_time, str(e))
            raise ValueError(f"Invalid date or format: {date_time}.") from e

    def translator(self, word: str, language: str = LANGUAGE) -> str:
        """
        Translate a given English word into a specified language.

        The function takes an English word and translates it into Polish, German, or Spanish based on the specified language. 
        It currently supports translation of days of the week and the word 'training'.

        Parameters:
        - word (str): The English word to be translated. Supported words are 'training', 'monday', 'tuesday', 'wednesday', 
                    'thursday', 'friday', 'saturday', and 'sunday'.
        - language (str, optional): The target language for translation. Defaults to the class constant LANGUAGE. 
                                    Supported languages are 'polski', 'german', and 'spanish'.

        Returns:
        - str: The translated word in the specified language.

        Raises:
        - KeyError: If the input word is not in the supported list of words.

        Examples:
        - translator('monday', 'polski') -> 'poniedziałek'
        - translator('training', 'spanish') -> 'ejercicio'
        """
        translations = {
            'polski': {'training': 'trening', 'monday': 'poniedziałek', 'tuesday': 'wtorek', 'wednesday' : 'środa', 'thursday' : 'czwartek', 'friday' : 'piątek', 'saturday' : 'sobota', 'sunday' : 'niedziela'},
            'german': {'training': 'training', 'monday': 'montag', 'tuesday': 'dienstag', 'wednesday' : 'mittwoch', 'thursday' : 'donnerstag', 'friday' : 'freitag', 'saturday' : 'samstag', 'sunday' : 'sonntag'},
            'spanish': {'training': 'ejercicio', 'monday': 'lunes', 'tuesday': 'martes', 'wednesday' : 'miércoles', 'thursday' : 'jueves', 'friday' : 'viernes', 'saturday' : 'sábado', 'sunday' : 'domingo'}
        }
        if language:
            try:
                return translations[language][word.lower()]
            except KeyError:
                if word.lower() in translations[language].values():
                    return word
                self.logger.warning("Translation for '%s' in '%s' not found. Using English word.", word, language)
                return word
        else:
            return word

    def format_date(self, value: str) -> str:
        """
        Format the date from the email header.

        Args:
            value (str): The date to format.

        Returns:
            str: The formatted date.
        """
        try:
            if "+0000" in value:
                if value.endswith(" (UTC)"):
                    value = value.rsplit(" ", 1)[0]
                original_date = datetime.strptime(
                    value, "%a, %d %b %Y %H:%M:%S %z"
                ) + timedelta(hours=2)
            else:
                original_date = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %z")
            return original_date.strftime("%d/%m/%Y %H:%M:%S")
        except ValueError as e:
            self.logger.error("Date formatting error: %s", str(e), exc_info=True)
            raise ValueError from e

    def string_to_datetime(self, datetime_string):
        """
        Convert a datetime string into a Python datetime object.

        This function supports multiple datetime formats and attempts to parse the input string
        using each of these formats. If the string doesn't match any of the known formats,
        the function raises a ValueError.

        Parameters:
        datetime_string (str): A string containing a datetime, intended to be converted into
                            a Python datetime object. The string can be in several formats,
                            such as "Mon, 23 Oct 2023 22:22:38 +0000" or "2023-10-23T22:22:38Z".

        Returns:
        datetime.datetime: A Python datetime object corresponding to the input string. If the input
                        string does not match any of the known formats, the function will raise
                        a ValueError.

        Raises:
        ValueError: If the input `datetime_string` does not match any of the known formats, a
                    ValueError is raised with a descriptive error message.
        """
        # Clean the datetime string if it ends with (UTC)
        if datetime_string.endswith(" (UTC)"):
            datetime_string = datetime_string.rsplit(" ", 1)[0]

        # List of potential datetime formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # e.g., "Mon, 23 Oct 2023 22:22:38 +0000"
            "%Y-%m-%d %H:%M:%S",  # e.g., "2023-10-23 22:22:38"
            "%Y/%m/%d %H:%M:%S",  # e.g., "2023/10/23 22:22:38"
            "%Y-%m-%dT%H:%M:%S",  # e.g., "2023-10-23T22:22:38"
            "%Y/%m/%dT%H:%M:%S",  # e.g., "2023/10/23T22:22:38"
            "%Y-%m-%d",  # e.g., "2023-10-23"
            "%Y/%m/%d",  # e.g., "2023/10/23"
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%MZ",
            "%Y-%m-%dT%HZ",
        ]
        for fmt in formats:
            try:
                # Attempt to create a datetime object using the current format
                datetime_object = (
                    datetime.strptime(
                        datetime_string,
                        fmt
                        )
                )
                return datetime.strptime(
                    datetime.strftime(
                        datetime_object,
                        "%d/%m/%Y %H:%M:%S"
                        ),
                    "%d/%m/%Y %H:%M:%S"
                    )
            except ValueError:
                continue
        raise ValueError(
            f"Time data '{datetime_string}' does not match any known format."
        )
