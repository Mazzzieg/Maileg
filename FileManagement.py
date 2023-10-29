import os
from datetime import datetime
import shutil
from UtilityFunctions import UtilityFunctions


class FileManagement:
    """
    Manages file operations related to user emails, including searching for credentials, cleaning text files, and managing lists of emails awaiting responses.

    This class provides methods for handling various file operations necessary for email management. It ensures user credentials are properly stored, maintains records of emails that require responses, and performs cleaning operations on text files to ensure they are readable and free of unnecessary whitespace.

    Attributes
    ----------
    user_mail : str
        The email address of the user for which file operations are being performed.
    logger : logging.Logger
        The logger instance used to log messages and operations performed by the class.
    folder_name : str
        Path to the folder where daily mail records are stored.
    mails_to_answer : dict
        A dictionary containing emails that need to be answered.
    sent_mails_waiting_for_answer_or_confirmation : dict
        A dictionary containing sent emails for which the user is awaiting a response or confirmation.

    Methods
    -------
    __init__(self, logger, user_mail: str)
        Constructs all the necessary attributes for the FileManagement object.
    creds_finder(self)
        Searches for the 'credentials.json' file in predefined locations and moves it to a user-specific directory.
    txt_file_cleaner(self) -> None
        Removes all blank spaces from an output text file to clean up the content.
    remove_from_waiting_list(self, sender_email: str) -> None
        Removes the specified email from the list of emails waiting for a response.
    add_to_waiting_list(self) -> None
        Adds emails to a file listing those awaiting a response.
    update_sent_mails_waiting_for_answer_from_file(self) -> None
        Updates the dictionary of emails awaiting a response based on the contents of a designated text file.
    save_message_content(self, one_message_keyword_filter: dict) -> None
        Writes answered mail to a .txt file.
    """

    def __init__(self, logger, user_mail: str):
        """
        Initializes the FileManagement class with the user's email and a logger instance.

        Parameters
        ----------
        logger : logging.Logger
            The logger instance to be used for logging messages and operations.
        user_mail : str
            The user's email address for identifying the relevant directories and files.
        """
        self.user_mail: str = user_mail
        self.logger = logger
        if not os.path.exists(f"./users/{self.user_mail}/mails"):
            os.makedirs(f"./users/{self.user_mail}/mails")
        self.folder_name: str = f"./users/{self.user_mail}/mails/{datetime.today().strftime('%Y-%m-%d')}.txt"
        self.mails_to_answer: dict = {}
        self.sent_mails_waiting_for_answer_or_confirmation: dict = {}
        self.utility = UtilityFunctions(self.logger)

    def creds_finder(self):
        """
        Searches for a user's credentials file in predefined locations and moves it to a user-specific directory.

        This method looks for a 'credentials.json' file in several predefined locations. If the file is found,
        it is moved to a 'users/{user_mail}' directory. The search stops after finding and moving the file
        from the first location. If the file is not found in any of the predefined locations, a FileNotFoundError
        is raised. If an error occurs during the file operation, it is logged and the respective exception is raised.

        Raises:
            FileNotFoundError: Raised if the credentials file is not found in any of the expected locations.
            OSError: Raised for operating system-related errors like 'file not found' or 'permission issues'.
            Exception: Raised for any other unexpected issues that occur while moving the credentials file.
        """
        locations_to_check = [
            "./credentials.json",
            os.path.expanduser("~/Downloads/credentials.json"),
            os.path.expanduser(f"~/Downloads/{self.user_mail}.json"),
            os.path.expanduser("~/Desktop/credentials.json"),
            os.path.expanduser(f"~/Desktop/{self.user_mail}.json"),
        ]
        file_found = False
        for location in locations_to_check:
            if os.path.exists(location):
                try:
                    destination_dir = f"users/{self.user_mail}"
                    if not os.path.exists(destination_dir):
                        os.makedirs(destination_dir)
                    shutil.move(location, f"{destination_dir}/{self.user_mail}.json")
                    file_found = True
                    break  # stop after moving the file from the first location found
                except OSError as e:
                    # Specific error handling for OSError, which includes file not found and permission issues
                    self.logger.error(
                        "An operating system error occurred while moving the credentials file: %e",
                        e,
                    )
                    raise
                except Exception as e:
                    # General error handling for other exceptions
                    self.logger.error(
                        "An unexpected error occurred while moving the credentials file: %e",
                        e,
                    )
                    raise
        if not file_found:
            error_message = "Credentials file not found in any of the expected locations. Please ensure 'credentials.json' is available."
            self.logger.error(error_message)
            raise FileNotFoundError(error_message)

    def txt_file_cleaner(self) -> None:
        """
        Erase all the blank spaces in an output file.

        Args:
            file (str): The file path to clean.
        """
        cleaned = []
        with open(self.folder_name, "r", encoding="utf-8") as r:
            for line in r:
                if line.strip():
                    cleaned.append(line)
        with open(self.folder_name, "w", encoding="utf-8") as w:
            for line in cleaned:
                w.write(line)

    def remove_from_waiting_list(self, sender_email: str) -> None:
        """
        Update the list of emails waiting for a response.

        Args:
            sender_email (str): The email address that has been responded to.
        """
        try:
            file_path = f"./users/{self.user_mail}/mails_waiting_for_answer.txt"
            with open(file_path, "r", encoding="UTF-8") as f:
                lines = [line for line in f if sender_email not in line]

            with open(file_path, "w", encoding="UTF-8") as f:
                f.writelines(lines)
        except Exception as e:
            self.logger.error("Error updating waiting list: %s", e, exc_info=True)

    def add_to_waiting_list(self) -> None:
        """
        Update the list of emails waiting for a response.
        """
        with open(
            f"./users/{self.user_mail}/mails_waiting_for_answer.txt",
            "a",
            encoding="UTF-8",
        ) as f:
            for (
                customers_mail,
                date_of_responce,
            ) in self.sent_mails_waiting_for_answer_or_confirmation.items():
                # Convert the stored date-time string to a datetime object
                date_time_obj = datetime.strptime(date_of_responce, "%d/%m/%Y %H:%M:%S")
                # Reformat the datetime object to the desired string format
                formatted_date_of_response = date_time_obj.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                f.write(f"\n  {customers_mail}: {formatted_date_of_response}")

    def update_sent_mails_waiting_for_answer_from_file(self) -> None:
        """
        Update the dictionary tracking emails for which the user awaits a response.

        This method reads entries from a designated text file, each containing an email address and a timestamp,
        then updates a dictionary that maps email addresses to datetime objects indicating when a response was received.
        The file is expected to reside in a user-specific directory and its entries are in the format:
        'email: YYYY-MM-DDTHH:MM:SSZ'.

        If the file does not exist, the method simply returns without making any changes. If an unexpected error occurs
        while reading the file, the method logs the error with full traceback information for debugging purposes and
        re-raises the exception, allowing the calling code to handle it.

        Expected file format for each line:
            email: YYYY-MM-DDTHH:MM:SSZ

        Raises:
            Exception: If an unforeseen error occurs during file reading, the exception is logged and then re-raised
                    to be handled by the calling context.
        """
        file_path = f"./users/{self.user_mail}/mails_waiting_for_answer.txt"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="UTF-8") as f:
                    for line in f:
                        parts = [part.strip() for part in line.strip().split(":", 1)]
                        if len(parts) == 2:
                            email, date_time_str = parts
                            try:
                                date_time_obj = self.utility.string_to_datetime(
                                    date_time_str
                                )
                                self.sent_mails_waiting_for_answer_or_confirmation[
                                    email
                                ] = date_time_obj
                            except ValueError:
                                self.logger.error(
                                    "Invalid date format for 'receiving_time': %s."
                                    "Expected format is 'YYYY-MM-DDTHH:MM:SSZ'.",
                                    date_time_str,
                                )
                                raise ValueError
                        elif len(parts) == 1 and not parts[0]:
                            pass
                        else:
                            self.logger.error(
                                "Invalid line format in %s: %s. "
                                "Expected format is 'email: YYYY-MM-DDTHH:MM:SSZ'. Skipping...",
                                file_path,
                                line,
                            )
            except Exception as e:
                self.logger.error(
                    "An unexpected error occurred while reading the file: %s",
                    e,
                    exc_info=True,
                )
                raise

    def save_message_content(self, one_message_keyword_filter: dict) -> None:
        """
        Save the content of the already answered first message from a new customer to a .txt file.
        """
        with open(self.folder_name, "a", errors="ignore", encoding="utf-8") as f:
            for key, message_value in one_message_keyword_filter.items():
                f.write(f"\n  {key.title()}:")
                f.write(f"\n  {message_value}")
            f.write("\n" + "=" * 50)
