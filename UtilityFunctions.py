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

    def day_of_a_week(self, date_time: str, language: str = LANGUAGE) -> str:
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
            str: The day of the week in Polish.
        """
        if language.lower() == "polski":
            weekdays = {
                0: "Poniedziałek",
                1: "Wtorek",
                2: "Środa",
                3: "Czwartek",
                4: "Piątek",
                5: "Sobota",
                6: "Niedziela",
            }
        if language.lower() == "german":
            weekdays = {
                0: "Montag",
                1: "Dienstag",
                2: "Mittwoch",
                3: "Donnerstag",
                4: "Freitag",
                5: "Samstag",
                6: "Sonntag",
            }
        if language.lower() == "spanish":
            weekdays = {
                0: "Lunes",
                1: "Martes",
                2: "Miércoles",
                3: "Jueves",
                4: "Viernes",
                5: "Sábado",
                6: "Domingo",
            }
        else:
            weekdays = {
                0: "Monday",
                1: "Tuesday",
                2: "Wednesday",
                3: "Thursday",
                4: "Friday",
                5: "Saturday",
                6: "Sunday",
            }
        try:
            date = date_time.split("T")[0]
            date_parsed = datetime.strptime(date, "%Y-%m-%d")
        except ValueError as e:
            self.logger.error("Error parsing date string %s: %e", date_time, str(e))
            raise ValueError(
                f"Invalid date or format: {date_time}. Expected format: 'YYYY-MM-DDTHH:MM:SSZ'"
            ) from e
        except Exception as e:
            self.logger.error(
                "Unexpected error when parsing date string %s : %e", date_time, str(e)
            )
            raise
        weekday_value = datetime.weekday(date_parsed)
        return weekdays[weekday_value]

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
