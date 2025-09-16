from assistant.activities.check_status import is_online

online = is_online()

if online:
    from assistant.core.mouth import speak
else:
    from assistant.core.mouth2 import speak
