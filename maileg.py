from datetime import datetime
import logging
from logging import Logger
import os
import sys

from google.auth.exceptions import TransportError  # type: ignore

from ApiInteraction import ApiInteraction
from FileManagement import FileManagement
from config import USER_EMAIL, KEYWORDS


class Maileg:
    """
    Handles interactions with Gmail and Google Calendar via their respective APIs,
    facilitating the management and automated responses to emails and calendar scheduling.

    This class utilizes methods to authenticate with Gmail and Google Calendar,
    search for specific emails, update their status, parse and filter email content,
    respond to received emails, and manage calendar events. It also provides
    functionalities for workout scheduling and customer response handling, among others.

    Attributes
    ----------
    user_mail : str
        The email address associated with the Gmail and Google Calendar account.
    keywords : list of str
        Keywords used to search and filter relevant emails.

    Methods
    -------
    __init__(self, mail: str, keywords: list)
        Constructs all the necessary attributes for the Maileg object.
    logging_configure(self)
        Sets up a custom logger specific to the user's email address.
    main(self, how_many_days: int)
        Orchestrates the email search, filtering, response, and calendar event scheduling based on user settings.
    """

    def __init__(self, mail: str = USER_EMAIL, keywords: list = KEYWORDS):
        """
        Initializes a new instance of the Maileg class with specific user email and keywords.

        Parameters
        ----------
        mail : str
            User's email address for the Gmail and Google Calendar account.
        keywords : list of str
            List of keywords to use when searching and filtering emails.
        """
        self.user_mail: str = mail
        self.keywords: list = keywords

        self.logger = self.logging_configure()
        self.logger.info("START OF A SCRIPT")
        try:
            self.api_interactor = ApiInteraction(
                self.logger, self.keywords, self.user_mail
            )
            self.api_interactor.authenticate()
        except TransportError:
            self.logger.error("There is no internet connection.")
            sys.exit(
                "There is NO INTERNET CONNECTION. Please make sure you have access to the internet and try running the script again."
            )
        self.gmail_service = self.api_interactor.gmail_service
        self.calendar_service = self.api_interactor.calendar_service

        self.file_manager = FileManagement(self.logger, self.user_mail)

    def logging_configure(self) -> Logger:
        """
        Configures the logging for tracking the operations of the Maileg instance.

        The logger is customized to store logs in a user-specific directory, creating a new log file each day.
        Log files are named after the current date for ease of reference.

        Returns
        -------
        logging.Logger
            A configured Logger instance that logs events tied to the user's email, storing them in daily log files.
        """
        logging_path = (
            f"./users/{self.user_mail}/logs/{datetime.today().strftime('%Y-%m-%d')}.log"
        )
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        if not os.path.exists(f"./users/{self.user_mail}/logs"):
            os.makedirs(f"./users/{self.user_mail}/logs")
        logging.basicConfig(
            level=logging.INFO,
            filename=logging_path,
            encoding="utf-8",
            format=log_format,
            datefmt=date_format,
        )
        logger = logging.getLogger(self.user_mail)

        if not logger.hasHandlers():
            log_path = logging_path
            handler = logging.FileHandler(log_path)
            formatter = logging.Formatter(log_format, datefmt=date_format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def main(self, how_many_days: int):
        """
        Executes the main operations of the Maileg instance for email management and calendar scheduling.

        Retrieves and processes emails from the past specified number of days, filters them based on pre-set
        conditions, and handles automated email responses and calendar event scheduling.

        Parameters
        ----------
        how_many_days : int
            Number of past days from which to retrieve and process emails.
        """
        # Get emails that match the specified query
        results = self.api_interactor.search_messages(
            f"to:me newer_than:{str(how_many_days)}d Is:unread"
        )
        self.logger.info("Found %s result(s).", len(results))
        print(f"Found {len(results)} result(s).")

        # If the script is run more than once per day, remove the previous output file
        if results and os.path.isfile(self.file_manager.folder_name):
            os.remove(self.file_manager.folder_name)

        # For each matched email, read and filter it
        for message in results:
            self.api_interactor.read_message(message)
            self.api_interactor.received_email_filters()

        # Remove 'unread' label from analyzed emails to prevent reprocessing
        self.api_interactor.mark_as_read(
            f"to:me newer_than:{str(how_many_days)}d Is:unread"
        )

        if self.api_interactor.something_happened is False:
            print("Everything is working fine and there was nothing to do :)")
