from winotify import Notification

# Absolute path to the application icon file
# Used for Windows toast notifications to provide brand identification
icon_path = r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\logo.ico"


def notification(title, message):
    """
    Display a Windows toast notification with custom title and message.
    
    Creates and shows a system notification using the Windows Toast API
    (winotify library). Notifications appear in the Windows Action Center
    and can be used for alerts, reminders, or status updates.
    
    Args:
        title (str): The main title/header of the notification.
                    Displayed in bold at the top of the toast.
        message (str): The detailed message content of the notification.
                      Provides context or additional information.
    
    Features:
        - Uses custom J.A.R.V.I.S. application identifier
        - Long duration display (until user dismisses or timeout)
        - Custom icon for brand recognition
        - Persistent in Windows Action Center
    
    Examples:
        >>> notification("System Update", "Update completed successfully")
        # Shows a notification with title "System Update" and the message
    
        >>> notification("Reminder", "Meeting in 15 minutes")
        # Shows a reminder notification
    
    Note:
        Requires the winotify package and Windows 10 or later for proper
        functionality. The notification will appear in the system tray
        and remain in the Action Center until dismissed.
    """
    toast = Notification(
        app_id="🟢 J.A.R.V.I.S.",  # Application identifier shown in Action Center
        title=title,               # Notification title text
        msg=message,               # Notification message body
        duration="long",           # Notification stays until manually dismissed
        icon=icon_path,            # Custom icon for visual identification
    )
    toast.show()


if __name__ == "__main__":
    """
    Demonstration of the notification functionality.
    
    When run as a standalone script, this displays a test notification
    to verify that the notification system is working correctly.
    """
    notification("hi", "hello")