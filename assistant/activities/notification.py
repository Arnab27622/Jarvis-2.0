from winotify import Notification

icon_path = r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\logo.ico"


def notification(title, message):
    toast = Notification(
        app_id="🟢 J.A.R.V.I.S.",
        title=title,
        msg=message,
        duration="long",
        icon=icon_path,
    )
    toast.show()


if __name__ == "__main__":
    notification("hi", "hello")
