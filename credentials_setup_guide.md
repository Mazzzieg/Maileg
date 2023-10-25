Credentials Setup Guide

This guide provides a step-by-step procedure on how to set up your Google API credentials for the Maileg script. These credentials are necessary for the script to access and interact with your Gmail and Google Calendar.

Step 1: Google Developers Console

Navigate to Google Developers Console.
Log in with your Google account (the same one you intend to use with Maileg).

Step 2: Create a New Project

Click on the project drop-down on the top right corner of the page.
Click on the "New Project" button on the top right of the modal.
Enter a Project Name, for example, "Maileg".
Click the "Create" button.

Step 3: Enable APIs

Click on the "Navigation menu" (three horizontal lines) on the top left corner of the page.
Select "API & Services" > "Library".
Search for "Gmail API" and select it from the results. Click on the "Enable" button.
Repeat this process for the "Google Calendar API".

Step 4: Create Credentials

Click "Create Credentials" on the top of the page.
Select "OAuth client ID" from the drop-down.
If this is your first time creating credentials, you may need to configure the OAuth consent screen. Fill in the necessary information. For the user type, select "External" and fill in the necessary information.

Once the OAuth consent screen is configured, select "Desktop app" as the Application type, give it a name (e.g., "MailegClient"), and click "Create".
Close the modal showing your client ID and client secret by clicking "OK".


Step 5: Download Credentials
You will be redirected to the "Credentials" tab under "APIs & Services".
Find the "OAuth 2.0 Client IDs" section, and you will see your newly created credentials.
Click the download button on the right side (it looks like a small down arrow). 

This will download a JSON file containing your credentials.

Rename this file to credentials.json and place it in the root directory of your Maileg project (Optional)


Step 6: Enable the Google Sheets API (Optional)
If you intend to use Google Sheets with Maileg, repeat Step 3 for the "Google Sheets API".

By following these steps, you'll have the credentials.json needed for the Maileg script to authenticate and interact with Google services on your behalf. Be sure not to share your credentials.json file with others, as it allows access to your Google data.