"""
Configuration settings for the Maileg script. Set the variables to suit your specific needs.
"""

# Gmail settings
USER_EMAIL : str = 'your-email@gmail.com'  # Your Gmail address
# Keywords that might be used by customer in mail, that script will be filtering and searching for
KEYWORDS : list = ['keyword_1', 'keyword_2']
CALENDAR_OPTIONAL_HOUR_NAME : str = 'wolne' # NOT case-sensitive 
# Email settings

def auto_reply(workouts):
    """
    Function generating answer to a first mail.
    """
    # Message for auto-reply emails
    reply = f"""
Dear [Customer],

Thank you for reaching out to us. This is an automated response confirming that we have received your email.
We will get back to you as soon as possible.

{workouts}

Best Regards,
[Your Name]
"""
    return reply

def auto_confirmation(workout_datetime, location):
    """
    Function generating confirmation of scheduling a workout.
    """
    # Message for confirmation emails
    reply = f"""
Dear [Customer],

This is a confirmation of scheduling your workout at {workout_datetime} in {location}.
Can't wait to see you there!

Best Regards,
[Your Name]
"""
    return reply
