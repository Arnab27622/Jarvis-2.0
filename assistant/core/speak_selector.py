# speak_selector.py (modified for queue-based streaming)
from assistant.activities.check_status import is_online

online = is_online()

if online:
    from assistant.core.mouth import (
        speak,
        speak_streaming,
        wait_for_tts_completion,
        start_tts_consumer,
        stop_tts_consumer,
    )
else:
    from assistant.core.mouth2 import (
        speak,
        speak_streaming,
        wait_for_tts_completion,
        start_tts_consumer,
        stop_tts_consumer,
    )
