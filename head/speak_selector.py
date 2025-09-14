from function.check_status import is_online

online = is_online()

if online:
    from head.mouth import speak
else:
    from head.mouth2 import speak
