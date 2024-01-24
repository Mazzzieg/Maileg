import os
import sys
import logging
from datetime import datetime
import argparse

from google.auth.exceptions import TransportError, RefreshError  # type: ignore # pylint: disable=import-error

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
        Orchestrates the email search, filtering, response,
        and calendar event scheduling based on user settings.
    """

    def __init__(self, mail: str = USER_EMAIL, keywords: list = KEYWORDS, args = None):
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
        self.args = args

        self.logger = self.logging_configure()
        self.api_interactor = ApiInteraction(
            self.logger,
            self.keywords,
            self.user_mail
            )
        self.file_manager = FileManagement(
            self.logger,
            self.user_mail
            )

    def logging_configure(self) -> logging.Logger:
        """
        Configures the logging for tracking the operations of the Maileg instance.

        The logger is customized to store logs in a user-specific directory,
        creating a new log file each day.
        Log files are named after the current date for ease of reference.

        Returns
        -------
        logging.Logger
            A configured Logger instance that logs events tied to the user's email,
            storing them in daily log files.
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

    def authenticate_api(self) -> None:
        """
        Authenticates with the Google API and initializes the API interaction services.
        """
        try:
            self.api_interactor.authenticate()
        except RefreshError:
            self.logger.error("Token expired. Re-authenticating with a new token.")
            self.handle_token_refresh()
        except TransportError:
            self.logger.error("No internet connection.")
            sys.exit("No internet connection. Please check your network and try again.")

    def handle_token_refresh(self) -> None:
        """
        Handles the refresh of the Google API token.
        """
        token_path = f"./users/{self.user_mail}/token.pickle"
        if os.path.exists(token_path):
            os.remove(token_path)
        self.api_interactor.authenticate()
        os.system('cls' if os.name == 'nt' else 'clear')

    def process_emails(self, how_many_days: int) -> None:
        """
        Processes emails from the specified number of past days.

        This method retrieves all unread emails from the past 'how_many_days' and processes each one.
        It calls 'process_individual_email' for each email and then 'finalize_email_processing'
        to handle post-processing tasks.

        Parameters
        ----------
        how_many_days : int
            The number of days in the past from which to process unread emails.
        """
        results = self.api_interactor.search_messages(f"to:me newer_than:{how_many_days}d Is:unread")
        print(f"Recieved {len(results)} message(s).")
        self.logger.info("Received %s message(s).", len(results))
        for message in results:
            self.process_individual_email(message)

    def process_individual_email(self, message) -> None:
        """
        Processes an individual email message.

        This method reads a single email message and applies any necessary filtering
        as defined in the 'ApiInteraction' class. It's typically called for each email
        retrieved by 'process_emails'.
        Parameters
        ----------
        message : dict
            A dictionary representing an email message, typically including details like message ID.
        """
        self.api_interactor.read_message(message)
        self.api_interactor.received_email_filters()

    def answering_to_mails(self, without_answering_mode: bool = False) -> None:
        """
        Finalizes the email processing routine.

        This method performs the final steps in the email processing workflow. It involves responding to
        new messages filtered as questions and marking processed emails as read to prevent reprocessing.
        It also provides feedback on the overall process completion.

        Notes
        -----
        This method relies on the 'ApiInteraction' instance for operations like marking emails as read
        and responding to messages.
        """
        if self.api_interactor.mails_to_answer:
            self.logger.info(
                "Recieved %s new message(s) filtered as QUESTION(S).",
                len(self.api_interactor.mails_to_answer)
                )
            print(f"Recieved {len(self.api_interactor.mails_to_answer)} new message(s) filtered as QUESTION(S).")
            self.api_interactor.answering_to_first_mails(without_answering_mode)

    def removing_unread_label(self, query: str) -> None:
        if self.api_interactor.removing_unread_label_blocker is False:
            self.api_interactor.mark_as_read(query)

        if self.api_interactor.something_happened is False:
            print("Everything is working fine and there was nothing to do :)")
        else:
            print("DONE! :)")

    def main(self, how_many_days: int) -> None:
        """
        Main method orchestrating the email and calendar management process.

        Parameters
        ----------
        how_many_days : int
            Number of days to look back for processing emails.
        """
        self.logger.info("Starting email processing for the past %d days.", how_many_days)
        self.authenticate_api()
        self.gmail_service = self.api_interactor.gmail_service
        self.calendar_service = self.api_interactor.calendar_service
        self.process_emails(how_many_days)
        self.answering_to_mails(self.args.without_answering)

        self.removing_unread_label(f"to:me newer_than:{how_many_days}d Is:unread")
        self.logger.info("Email processing completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Maileg email processing script."
        )
    parser.add_argument(
        "--without_answering",
        action="store_true",
        help="Run script without sending answers."
        )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to look back for processing emails."
        )
    argps = parser.parse_args()

    # Create an instance of Maileg and run main method
    maileg_instance = Maileg(USER_EMAIL, KEYWORDS)
    maileg_instance.args = argps
    maileg_instance.main(argps.days)
