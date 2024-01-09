import os
import tempfile
from datetime import datetime
import shutil
from UtilityFunctions import UtilityFunctions

class FileManagement:
    """
    Manages file operations related to user emails, including searching for credentials,
    cleaning text files, and managing lists of emails awaiting responses.

    This class provides methods for handling various file operations necessary for email management.
    It ensures user credentials are properly stored,
    maintains records of emails that require responses, and performs cleaning operations
    on text files to ensure they are readable and free of unnecessary whitespace.

    Attributes
    ----------
    user_mail : str
        The email address of the user for which file operations are being performed.
    logger : logging.Logger
        The logger instance used to log messages and operations performed by the class.
    folder_name : str
        Path to the folder where daily mail records are stored.
        A dictionary containing emails that need to be answered.
    sent_mails_waiting_for_answer_or_confirmation : dict
        A dictionary containing sent emails for which
        the user is awaiting a response or confirmation.

    Methods
    -------
    __init__(self, logger, user_mail: str)
        Constructs all the necessary attributes for the FileManagement object.
    creds_finder(self)
        Searches for the 'credentials.json' file in predefined locations
        and moves it to a user-specific directory.
    txt_file_cleaner(self) -> None
        Removes all blank spaces from an output text file to clean up the content.
    remove_from_waiting_list(self, sender_email: str) -> None
        Removes the specified email from the list of emails waiting for a response.
    add_to_waiting_list(self) -> None
        Adds emails to a file listing those awaiting a response.
    update_sent_mails_waiting_for_answer_from_file(self) -> None
        Updates the dictionary of emails awaiting a response based
        on the contents of a designated text file.
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
        self.sent_mails_waiting_for_answer_or_confirmation: list = []
        self.utility = UtilityFunctions(self.logger)
        self.setup_user_directories()

    def setup_user_directories(self):
        """
        Set up necessary directories for the user's email management.

        This method creates a directory structure under the './users/{user_email}' path to organize email-related files. 
        It ensures that the base user directory, a 'mails' subdirectory, and a subdirectory for the current date exist.
        The method also initializes the 'folder_name' attribute to the path of today's directory and 
        the 'file_name' attribute to a timestamped text file within this directory. 
        These paths are used for storing and managing email-related files.

        Directories created:
        - './users/{user_email}': The base directory for the user.
        - './users/{user_email}/mails': Subdirectory for storing mail-related files.
        - './users/{user_email}/mails/{YYYY-MM-DD}': Subdirectory for storing files specific to the current date.

        Attributes Set:
        - folder_name (str): Path to the current day's directory for storing email files.
        - file_name (str): Path to a timestamped text file within the current day's directory for logging or record-keeping.
        """
        user_dir = f"./users/{self.user_mail}"
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        mails_dir = f"{user_dir}/mails"
        if not os.path.exists(mails_dir):
            os.makedirs(mails_dir)
        today_dir = f"{mails_dir}/{datetime.today().strftime('%Y-%m-%d')}"
        if not os.path.exists(today_dir):
            os.makedirs(today_dir)
        self.folder_name = today_dir
        self.file_name = f"{today_dir}/{datetime.today().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

    def creds_finder(self):
        """
        Searches for a user's credentials file in predefined locations
        and moves it to a user-specific directory.

        This method looks for a 'credentials.json' file in several predefined locations.
        If the file is found, it is moved to a 'users/{user_mail}' directory.
        The search stops after finding and moving the file from the first location.
        If the file is not found in any of the predefined locations, a FileNotFoundError
        is raised. If an error occurs during the file operation,
        it is logged and the respective exception is raised.

        Raises:
            FileNotFoundError:
                Raised if the credentials file is not found in any of the expected locations.
            OSError:
                Raised for operating system-related errors like 'file not found' or 'permission issues'.
            Exception:
                Raised for any other unexpected issues that occur while moving the credentials file.
        """
        locations_to_check = [
            "./credentials.json",
            f"./{self.user_mail}.json",
            os.path.expanduser(f"./users/{self.user_mail}/credentials.json"),
            os.path.expanduser(f"./users/{self.user_mail}/{self.user_mail}.json"),
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
                    # Stop after moving the file from the first location found
                    break
                except OSError as e:
                    # Specific error handling for OSError,
                    # which includes file not found and permission issues
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
        Erase all the blank spaces from lines in a text file.

        This method reads a text file line by line, removes lines that contain only whitespace, 
        and writes the cleaned content back to the file. It operates in a memory-efficient way 
        and ensures the original file is replaced only after successful processing.

        Args:
            file_path (str, optional): The path to the text file to be cleaned. 
                                    If not provided, uses the default file path set in the object.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            OSError: For issues like permission errors or IO errors during file operations.
        """

        if not os.path.exists(self.file_name):
            self.logger.error("File %s does not exist. Cannot clean non existing file.", self.file_name)

        temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8")
        try:
            with open(self.file_name, "r", encoding="utf-8") as file:
                for line in file:
                    if line.strip():
                        temp_file.write(line)
            temp_file.close()
            shutil.move(temp_file.name, self.file_name)
        except OSError as e:
            os.remove(temp_file.name)
            self.logger.error("Error processing file %s: %s", self.file_name, e)

    def remove_from_waiting_list(self, sender_email: str) -> None:
        """
        Update the list of emails waiting for a response.

        Args:
            sender_email (str): The email address that has been responded to.
        """
        file_path = f"./users/{self.user_mail}/mails_waiting_for_answer.txt"
        if not os.path.exists(file_path):
            self.logger.warning(f"File {file_path} not found.")
            return
        try:
            with open(file_path, "r", encoding="UTF-8") as f:
                lines = f.readlines()
            with open(file_path, "w", encoding="UTF-8") as f:
                f.writelines(line for line in lines if sender_email not in line)
        except Exception as e:
            self.logger.error("Error updating waiting list: %s", e, exc_info=True)
            raise

    def add_to_waiting_list(self) -> None:
        """
        Update the list of emails waiting for a response.
        """
        file_path = f"./users/{self.user_mail}/mails_waiting_for_answer.txt"
        with open(file_path, "a", encoding="UTF-8") as f:
            for dictionary_of_sender in self.sent_mails_waiting_for_answer_or_confirmation:
                for customers_mail, date_of_response in dictionary_of_sender.items():
                    if customers_mail and date_of_response:
                        f.write(f"\n  {customers_mail}: {date_of_response}")

    def update_sent_mails_waiting_for_answer_from_file(self) -> None:
        """
        Update the dictionary tracking emails for which the user awaits a response.

        This method reads entries from a designated text file,
        each containing an email address and a timestamp, then updates a dictionary
        that maps email addresses to datetime objects indicating when a response was received.
        The file is expected to reside in a user-specific directory
        and its entries are in the format: 'email: "D/M/Y H:M:S".

        If the file does not exist, the method simply returns without making any changes.
        If an unexpected error occurs while reading the file,
        the method logs the error with full traceback information
        for debugging purposes and re-raises the exception,
        allowing the calling code to handle it.

        Expected file format for each line:
            email: "D/M/Y H:M:S"

        Raises:
            Exception: If an unforeseen error occurs during file reading,
                    the exception is logged and then re-raised to be handled
                    by the calling context.
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
                                self.sent_mails_waiting_for_answer_or_confirmation.append(
                                    {email : date_time_obj})
                            except ValueError:
                                self.logger.error(
                                    "Invalid date format for 'receiving_time': %s."
                                    "Expected format is 'D/M/Y H:M:S'.",
                                    date_time_str,
                                )
                                raise ValueError
                        elif len(parts) == 1 and not parts[0]:
                            pass
                        else:
                            self.logger.error(
                                "Invalid line format in %s: %s. "
                                "Expected format is 'email: 'D/M/Y H:M:S'. Skipping...",
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
        with open(self.file_name, "a", errors="ignore", encoding="utf-8") as f:
            for key, message_value in one_message_keyword_filter.items():
                f.write(f"\n{key.title()}:\n{message_value}\n" + "=" * 50 + "\n")
