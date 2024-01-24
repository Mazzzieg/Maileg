# Standard library imports
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime
from email.mime.text import MIMEText
from functools import wraps
import os
import sys
import pickle
import re
import time
from typing import List, Dict, Any

# Third-party library imports
from googleapiclient.discovery import build  # type: ignore  # pylint: disable=import-error
from googleapiclient.errors import HttpError  # type: ignore # pylint: disable=import-error
from google.auth.transport.requests import Request  # type: ignore # pylint: disable=import-error
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore # pylint: disable=import-error
import html2text # type: ignore # pylint: disable=import-error

# Local application/library specific imports
from FileManagement import FileManagement
from UtilityFunctions import UtilityFunctions
from config import (
    auto_reply,
    auto_confirmation,
    workout_hour_form,
    CALENDAR_OPTIONAL_HOUR_NAME
    )

MAX_RETRIES = 3

def handle_api_errors(func):
    """
    A decorator to add automatic retry and exception handling mechanisms
    to functions that perform API calls.

    This decorator catches exceptions related to HTTP errors,
    server not found, and other general exceptions.
    In the case of specific HTTP errors (status codes 403, 500, 503),
    it implements a retry mechanism with a progressive delay.
    For other exceptions, it stops the execution and logs the error.
    If all retries fail, the last caught exception is re-raised.

    The wrapped function can be any function that performs API calls
    and may raise the mentioned exceptions.

    Args:
        func (Callable): The function to wrap. This function is expected to perform an API call.

    Returns:
        Callable: A new function wrapped with exception handling and retry mechanisms.

    Raises:
        HttpError: Re-raised when an HTTP error occurs and is not recoverable after all retries.
        ServerNotFoundError: Re-raised when a server-related error occurs.
        Exception: Re-raised when an unexpected error occurs and is not recoverable.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except HttpError as err:
                last_exception = err
                self.logger.warning("An HTTP error occurred: %s ", err)
                if err.resp.status in [500, 503]:
                    sleep_time = 2**attempt
                    print(
                        f"Attempt {attempt}/5 failed. Retying in {sleep_time} seconds..."
                    )
                    self.logger.warning(
                        "Error occurred. Retrying in %s seconds...", sleep_time
                    )
                    time.sleep(sleep_time)
                elif err.resp.status == 403:
                    self.logger.error(
                        "A 403 Forbidden error occurred: %s. Please check the API credentials or request parameters.",
                        err,
                    )
                    break
                else:
                    self.logger.error("An unrecoverable error occurred.")
                    break
            except Exception as err:
                last_exception = err
                self.logger.error("An unexpected error occurred: %s", err)
                break
        if last_exception:
            raise last_exception

    return wrapper


class ApiInteraction:
    """
    Manages interactions with the Google API, specifically Gmail and Google Calendar services.

    This class encapsulates the functionality for authenticating
    with the Google API and performing various operations on a user's Gmail
    and Google Calendar data. Operations include sending emails,
    searching for specific messages in Gmail, marking emails as read,
    and reading and processing customer responses from Gmail messages.
    It also manages the user's workout scheduling by reading customer's
    preferred workout hours from their responses.

    Attributes
    ----------
    user_mail : str
        The email address of the user, used for sending emails
        and making requests on behalf of this user.
    logger : logging.Logger
        The logger instance used to log messages and operations performed by the API interactions.
    keywords : list
        A list of keywords used for filtering emails.
    scopes : list
        The list of scopes for the Google API permissions.
    messages : list
        A list used to store messages retrieved from Gmail.
    counter : int
        A counter used for internal logic (e.g., counting specific occurrences).
    gyms : list
        A list of gyms for potential workout scheduling.
    list_of_optional_hours : list
        A list of optional workout hours sent to customers.
    file_management : FileManagement
        An instance of FileManagement class used for handling user credentials.
    utility : UtilityFunctions
        An instance of UtilityFunctions class used for various
        utility functions like date formatting.
    something_happened : bool
        A flag used to indicate if an important event (like receiving a specific email) happened.
     removing_unread_label_blocker : bool
        A flag used to indicate if some error occured and removing "UNREAD" label from processed should be blocked.
    """

    def __init__(self, logger, keywords: list, user_mail: str):
        self.user_mail: str = user_mail
        self.logger = logger
        self.keywords: list = keywords
        self.scopes: list = [
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/calendar",
        ]
        self.messages: list = []
        self.gyms: list = []
        self.dates: list = []
        self.mails_to_answer: list = []
        self.formatted_workout_strings: list = []
        self.list_of_optional_hours: list = []
        self.file_management = FileManagement(self.logger, self.user_mail)
        self.utility = UtilityFunctions(self.logger)
        self.something_happened = False
        self.removing_unread_label_blocker = False

    def authenticate(self) -> None:
        """
        Authenticate with Google and set up the Gmail and Calendar services.

        This method authenticates with Google and initializes both the Gmail and
        Calendar services using the same set of credentials. This means the `build`
        function will only be called once, even though two services are being initialized.
        """
        token_path = f"./users/{self.user_mail}/token.pickle"
        creds = None
        secrets_file = f"users/{self.user_mail}/{self.user_mail}.json"

        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                self.file_management.creds_finder()
                flow = InstalledAppFlow.from_client_secrets_file(
                    secrets_file, self.scopes
                )
                creds = flow.run_local_server(port=0)
                with open(token_path, "wb") as token:
                    pickle.dump(creds, token)

        self.gmail_service = (
            (build("gmail", "v1", credentials=creds)).users().messages()  # pylint:disable=maybe-no-member
        )
        self.calendar_service = build("calendar", "v3", credentials=creds)

    # Main functions
    def build_message(self, destination: str, subject: str, body: str) -> dict:
        """
        Builds a message for sending in send_message function.

        Args:
            destination (str): The recipient's email address.
            subject (str): The email subject.
            body (str): The email body content.

        Returns:
            dict: A dictionary containing the message data.
        """
        self.message = MIMEText(body)
        self.message["to"] = destination
        self.message["from"] = self.user_mail
        self.message["subject"] = subject
        return {"raw": urlsafe_b64encode(self.message.as_bytes()).decode()}

    @handle_api_errors
    def send_message(self, destination: str, subject: str, body: str) -> None:
        """
        Builds and sends a message.

        Args:
            destination (str): Email address of the recipient.
            subject (str): Subject of the email.
            body (str): Body text of the email.
        """
        return self.gmail_service.send(  # type: ignore # pylint:disable=maybe-no-member
            userId="me", body=self.build_message(destination, subject, body)
        ).execute()

    @handle_api_errors
    def search_messages(self, query: str) -> List[dict]:
        """
        Search for messages in the user's Gmail account based
        on a query using Gmail search operators.

        Args:
            query (str): The query string for searching messages.

        Returns:
            list: A list of retrieved Gmail messages.
        """
        result = self.gmail_service.list(userId="me", q=query).execute()  # type: ignore # pylint:disable=maybe-no-member
        if "messages" in result:
            self.messages.extend(result["messages"])
        while "nextPageToken" in result:
            page_token = result["nextPageToken"]
            result = self.gmail_service.list(userId="me", q=query, pageToken=page_token).execute()  # type: ignore # pylint:disable=maybe-no-member
            if "messages" in result:
                self.messages.extend(result["messages"])
        return self.messages

    @handle_api_errors
    def mark_as_read(self, query: str) -> None:
        """
        Mark emails as read by removing the 'UNREAD' label from scanned emails.

        Args:
            query (str): The query string to identify the emails to mark as read.
        """
        messages_to_mark = self.search_messages(query)
        if not messages_to_mark:
            print("There are no messages to be marked as 'read'.")
            self.logger.info("There are no messages to be marked as 'read'.")
            return None
        self.logger.info("Todays messages have been marked as read")
        return self.gmail_service.batchModify(  # type: ignore # pylint:disable=maybe-no-member
            userId="me",
            body={
                "ids": [msg["id"] for msg in messages_to_mark],
                "removeLabelIds": ["UNREAD"],
            },
        ).execute()

    def reading_answers(self) -> list:
        """
        Read customer answers and check for selected workout hours.

        Returns:
            list: The selected workout hour information as a list, if a match is found.
            None: If no match is found.
        """
        try:
            # Attempt to retrieve and format the email body content
            raw_body = self.one_message_keyword_filter.get("body", "")
            if ">" in raw_body:
                cleared_body = raw_body.split(">", 1)[0]
            if "**" in raw_body:
                cleared_body = raw_body.split("**", 1)[0]
            if cleared_body:
                filtered_body = (
                    cleared_body.replace("  ", " ").replace("\n", "")
                )
            else:
                filtered_body = (raw_body.replace("  ", " ").replace("\n", ""))
            filtered_body_without_spaces = filtered_body.lower().replace(" ", "")
        except Exception as e:
            self.logger.error("Error processing email body: %s", e)
            return []
        for item in self.list_of_optional_hours:
            try:
                date_time, _, location = item
                formatted_string = workout_hour_form(
                    date_time.split('T')[0],
                    self.utility.translator(self.utility.day_of_a_week(date_time)),
                    date_time.split('T')[1][0:-9],
                    location
                    )
                formatted_string_without_spaces = formatted_string.lower().replace(
                    " ", ""
                )
                # Check for a match in the customers response
                if (
                    formatted_string in filtered_body
                    or formatted_string_without_spaces in filtered_body_without_spaces
                ):
                    return item
            except ValueError:
                # Handle the case where item doesn't have the expected format
                self.logger.warning("Unexpected format in list_of_optional_hours.")
                continue
            except Exception as e:
                self.logger.error("Error processing optional hours: %s", e)
                continue
        return []  # No match was found

    # CONFIRMATION
    @handle_api_errors
    def sending_confirmation(
        self, sender_email: str, sender_choice: list, customer_name
    ) -> None:
        """
        Send a workout confirmation to a customer and remove their email from the waiting list.

        Args:
            sender_email (str): The customer's email address.
            sender_choice (list): Information about the selected workout hour.
        """
        date_time, _, location = sender_choice
        subject, confirmation_body = auto_confirmation(
            date_time.split('T')[0],
            self.utility.translator(self.utility.day_of_a_week(date_time)),
            date_time.split('T')[1][0:-9],
            self.utility.translator('training'),
            location,
            customer_name
            )
        self.send_message(
            sender_email,
            subject,
            confirmation_body,
        )
        print(f"Confirmation has been sent to {customer_name} - {sender_email}")
        self.something_happened = True
        self.file_management.remove_from_waiting_list(sender_email)

    # CALENDAR
    def schedule_workout(
        self, sender_email: str, sender_choice: list, customer_name
    ) -> None:
        """
        Try to schedule the workout based on the sender's choice.

        Args:
            sender_email (str): The sender's email address.
            sender_choice (list): The sender's workout choice.
        """
        try:
            for event in self.events:
                location = event.get("location", "")
                if (
                    sender_choice[0] == event["start"]["dateTime"]
                    and sender_choice[1].lower() == event["summary"].lower()
                    and sender_choice[2] == location
                ):
                    event_id = event["id"]
                    updated_event = (
                        self.calendar_service.events()  # pylint:disable=maybe-no-member
                        .get(
                            calendarId="primary", eventId=event_id
                        )
                        .execute()
                    )
                    new_attendee = {"email": sender_email}
                    if "attendees" in updated_event:
                        updated_event["attendees"].append(new_attendee)
                    else:
                        updated_event["attendees"] = [new_attendee]
                    updated_event["summary"] = f"{self.utility.translator('training').title()} - {customer_name}"
                    self.calendar_service.events().update(  # pylint:disable=maybe-no-member
                        calendarId="primary", eventId=event_id, body=updated_event
                    ).execute()
                    print("WORKOUT HAS BEEN SCHEDULED")
                    self.sending_confirmation(
                        sender_email, sender_choice, customer_name
                    )
                    break
        except StopIteration:
            print("COULDN'T FIND WORKOUT CHOSEN BY A CLIENT")

    @handle_api_errors
    def calendar_stuff(self) -> None:
        """
        Retrieve and process Google Calendar events to offer workout options to customers.
        """
        events_result = (
            self.calendar_service.events()  # pylint:disable=maybe-no-member
            .list(
                calendarId="primary",
                # 'Z' indicates UTC time,
                timeMin=datetime.utcnow().isoformat() + "Z",
                timeZone="UTC+1:00",
                maxResults=15,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        self.events = events_result.get("items", [])

        if not self.events:
            print("No upcoming events found.")
            print(
                f'CANNOT RESPOND TO ALL THE MAILS WITHOUT INFORMATION ABOUT AVAILABLE WORKOUTS ("{CALENDAR_OPTIONAL_HOUR_NAME}").'
            )
            self.logger.error("SCRIPT HAS BEEN STOPPED. CANNOT RESPOND TO ALL THE MAILS WITHOUT INFORMATION ABOUT AVAILABLE WORKOUTS")
            sys.exit(
                "Script has been stopped. Please provide the optional workout hours (IN YOUR CALENDAR) to proceed."
            )

        for event in self.events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            if str(event["summary"]).lower() == CALENDAR_OPTIONAL_HOUR_NAME:
                try:
                    location = str(event["location"])
                except KeyError:
                    self.logger.error(f"'{CALENDAR_OPTIONAL_HOUR_NAME}' hour planned {datetime.strptime(start.split("T")[0], "%Y-%m-%d").date()} at {start.split('T')[1][0:-9]} CANNOT BE proposed to the customer - NO LOCATION")
                    print(f"'{CALENDAR_OPTIONAL_HOUR_NAME}' hour planned {datetime.strptime(start.split("T")[0], "%Y-%m-%d").date()} at {start.split('T')[1][0:-9]} CANNOT BE proposed to the customer - NO LOCATION")
                    continue
                if location not in self.gyms:
                    self.gyms.append(location)
                self.list_of_optional_hours.append([start, event["summary"], location])
                date = datetime.strptime(start.split("T")[0], "%Y-%m-%d").date()
                if date not in self.dates:
                    self.dates.append(date)

        if len(self.list_of_optional_hours) < 15:
            if len(self.list_of_optional_hours) < 2:
                be = "is"
            else:
                be = "are"
            print(
                f"There {be} ONLY {len(self.list_of_optional_hours)} optional workout hour(s) found in day(s) {min(self.dates)} - {max(self.dates)}."
            )
            self.logger.warning(
                f"There {be} ONLY %s optional workout hour(s) found in day(s) %s - %s.",
                len(self.list_of_optional_hours),
                min(self.dates),
                max(self.dates),
            )

    # RECIEVED MAILS
    def extract_name_from_email(self, header_from):
        """
        Extracts the sender's name from the email header.
        If the name is absent, defaults to "Customer".
        """
        customer_name = header_from.split("<")[0].strip()
        customer_name = customer_name.replace('"', "")
        return customer_name

    def handle_response(self, sender_email: str) -> None:
        """
        Handle a response from a sender whose email we have been waiting for.

        Args:
            sender_email (str): The sender's email address.
        """
        if not self.list_of_optional_hours:
            self.calendar_stuff()

        sender_choice = self.reading_answers()
        if sender_choice:
            header_from = self.one_message_keyword_filter.get("from")
            customer_name = self.extract_name_from_email(header_from)
            self.schedule_workout(sender_email, sender_choice, customer_name)
        else:
            self.something_happened = True
            self.removing_unread_label_blocker = True
            print(
                "I couldn't find the client's choice of a workout. You have to do it manually :("
            )
            print(
                "I'm not removing the 'UNREAD' label from it so you'll see this mail and take care of it on yourself."
            )
            print(
                self.one_message_keyword_filter["body"]
                .split(">", 1)[0]
                .replace("\n", "")
            )

    def check_email_response_status(self, sender: str, receiving_time: str) -> str:
        """
        Determines if received emails are responses to previously sent emails.

        This method checks if the emails received from a specific sender are responses
        to emails that were already sent and are awaiting a reply, or if they are new
        inquiries. It compares the receiving time of the incoming email to the sending
        time of the sent email.
        Args:
            sender (str): The sender's email address.
            receiving_time (str): The time the email was received.

        Returns:
            str: Returns 'RESPONSE' if the email is identified as a response,
                'QUESTION' if it's identified as a new inquiry, or an empty string
                if it's neither.

        Raises:
            ValueError: If 'receiving_time' is not in the proper date format
            or if an invalid date is provided.
        """
        receiving_time_dt = self.utility.string_to_datetime(receiving_time)
        keys = list(set(key for d in self.file_management.sent_mails_waiting_for_answer_or_confirmation for key in d.keys()))
        if sender in keys:
            sent_time = [
                d[sender]
                for d in self.file_management.sent_mails_waiting_for_answer_or_confirmation
                if sender in d
                ][0]
            if (
                    receiving_time_dt > sent_time
                    ):
                return "RESPONSE"
        if (
                sender
                not in keys
            ):
            return "QUESTION"
        return ""

    def parse_parts_with_keywords(self, parts: list, mail: str) -> bool:
        """
        Parse the content of an email partition.

        Args:
            parts (list): A list of email parts.
            mail (str): The email message.

        Returns:
            bool: True if email parts are successfully parsed, False otherwise.
        """
        if parts:
            for part in parts:
                mime_type = part.get("mimeType")
                body = part.get("body")
                data = body.get("data")
                part_headers = part.get("headers")
                if part.get("parts"):
                    # Calling this function when we see that a part has parts inside
                    self.parse_parts_with_keywords(part.get("parts"), mail)
                if mime_type == "text/plain":
                    if data:
                        self.one_message_keyword_filter["body"] = urlsafe_b64decode(
                            data
                        ).decode()
                elif mime_type == "text/html":
                    if data:
                        self.one_message_keyword_filter[
                            "body"
                        ] = html2text.HTML2Text().handle(
                            urlsafe_b64decode(data).decode()
                        )
                else:
                    # Attachment other than a plain text or HTML
                    for part_header in part_headers:
                        part_header_name = part_header.get("name")
                        part_header_value = part_header.get("value")
                        if part_header_name == "Content-Disposition":
                            if "attachment" in part_header_value:
                                self.one_message_keyword_filter[
                                    "attachment"
                                ] = f"There is an attachment: {part.get('filename')}, size: {self.utility.get_size_format(self, body.get('size'))}."
            return True
        else:
            return False

    def parse_headers(self, headers: List[Dict[str, str]]) -> None:
        """
        Parse the headers of an email.

        Args:
            headers (List[Dict[str, str]]): The headers to parse.
        """
        for header in headers:
            name = header.get("name", "").lower()
            value = header.get("value", "")

            if name == "from":
                self.one_message_keyword_filter["from"] = value
            elif name == "to":
                self.one_message_keyword_filter["to"] = value
            elif name == "subject":
                self.one_message_keyword_filter["subject"] = value
            elif name == "date":
                self.one_message_keyword_filter["date"] = self.utility.format_date(
                    value
                )

    def parse_body(
        self, parts: List[Dict[str, Any]], payload: Dict[str, Any], mail: str
    ) -> None:
        """
        Parse the body of an email.

        Args:
            parts (List[Dict[str, Any]]): The parts to parse.
            payload (Dict[str, Any]): The payload of the email.
            mail (str): The email data.
        """
        if not self.parse_parts_with_keywords(parts, mail):
            body_data = payload.get("body", {}).get("data")
            if body_data:
                try:
                    decoded_body = urlsafe_b64decode(body_data).decode()
                    self.one_message_keyword_filter[
                        "body"
                    ] = html2text.HTML2Text().handle(decoded_body)
                except Exception as e:
                    self.logger.error(
                        "Error decoding message body: %s", e, exc_info=True
                    )

    @handle_api_errors
    def read_message(self, mail: str) -> None:
        """
        Read a received email and filter its content.

        Args:
            mail (str): The email message to read and filter.
        """
        self.one_message_keyword_filter: dict = {}

        msg = self.gmail_service.get(
            userId="me", id=mail["id"], format="full"  # type: ignore
            ).execute()

        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        parts = payload.get("parts", [])

        self.parse_headers(headers)
        self.parse_body(parts, payload, mail)

    # FIRST MAIL
    def received_message_filer_first_mail(self) -> bool:
        """
        Filter received emails for those containing any of
        the delivered keywords and return a boolean value.

        Returns:
            bool: True if keywords are found in the email, False otherwise.
        """
        for keyword in self.keywords:
            for value in self.one_message_keyword_filter.values():
                if keyword.lower() in value.lower():
                    return True
        return False

    def prepare_workout_options(self) -> str:
        """
        Prepare a string of available workout options.

        Returns:
            str: A string representing the available workout options.
        """
        if not self.formatted_workout_strings:
            for item in self.list_of_optional_hours:
                date_time, _, location = item
                self.formatted_workout_strings.append(
                    workout_hour_form(
                        date_time.split('T')[0],
                        self.utility.translator(self.utility.day_of_a_week(date_time)),
                        date_time.split('T')[1][0:-9],
                        location))
        return "\n".join(self.formatted_workout_strings)

    def answering_to_first_mails(self, without_answering_mode : bool = False) -> None:
        """
        Answer the first email that passed the filter
        and is from a new customer (not waiting for an answer/confirmation).
        """
        if self.mails_to_answer:
            if not self.list_of_optional_hours:
                self.calendar_stuff()
            workout_options = self.prepare_workout_options()
            if not without_answering_mode:
                for mail in self.mails_to_answer:
                    body = auto_reply(mail[2], workout_options)
                    self.send_message(mail[0], f"RE:{mail[1]}", body)
                    print(f"Response has been sent to {mail[2]} - {mail[0]}")
                    self.file_management.sent_mails_waiting_for_answer_or_confirmation.append(
                        {mail[0] : datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
                        )
                self.file_management.add_to_waiting_list()
            if without_answering_mode:
                for mail in self.mails_to_answer:
                    prepared_responce_folder = f"./users/{self.user_mail}/prepared_responce_file/{datetime.now().strftime("%Y-%m-%d")}"
                    prepared_responce_file = f"./users/{self.user_mail}/prepared_responce_file/{datetime.now().strftime("%Y-%m-%d")}/{datetime.now().strftime("%H-%M-%S")}.txt"
                    if not os.path.exists(prepared_responce_folder):
                        os.makedirs(prepared_responce_folder)
                    body = auto_reply(mail[2], workout_options)
                    with open(prepared_responce_file, 'w', encoding='UTF-8', newline='\n') as f:
                        f.write(f"Destination - {mail[0]}")
                        f.write(f"\nSubject - RE:{mail[1]}")
                        f.write(f"\nBody - {body}")
                    print(f"Response to {mail[2]} - {mail[0]} has been prepared and saved to the {prepared_responce_file}")
        else:
            if not self.something_happened:
                print("I've done nothing because.... There is nothing to do!")

    def handle_new_message(self, sender_email: str) -> None:
        """
        Handle a new message that is not a response to our mail.

        Args:
            sender_email (str): The sender's email address.
        """
        if self.received_message_filer_first_mail():
            header_from = self.one_message_keyword_filter.get("from")
            customer_name = self.extract_name_from_email(header_from)
            self.mails_to_answer.append((sender_email, self.one_message_keyword_filter["subject"], customer_name))  # type: ignore
            self.file_management.save_message_content(self.one_message_keyword_filter)
            self.file_management.txt_file_cleaner()
            self.something_happened = True

    def received_email_filters(self) -> None:
        """
        Filter received emails, process customer responses, and schedule workouts if necessary.
        """
        if "from" in self.one_message_keyword_filter:
            match = re.search(r"<([^>]+)>", self.one_message_keyword_filter["from"])
            if match:
                sender_email = match.group(1)
        else:
            sender_email = None
        if not sender_email:
            self.logger.error("No sender email found.")
            return

        if not self.file_management.sent_mails_waiting_for_answer_or_confirmation:
            self.file_management.update_sent_mails_waiting_for_answer_from_file()

        response_status = self.check_email_response_status(
            sender_email, self.one_message_keyword_filter["date"]
        )
        if response_status == "RESPONSE":
            self.handle_response(sender_email)
        if response_status == "QUESTION":
            self.handle_new_message(sender_email)
        if response_status is False:
            self.logger.error("UNKNOWN MESSAGE STATUS")
            raise UserWarning
