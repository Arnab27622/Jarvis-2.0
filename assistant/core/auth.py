import cv2
import face_recognition
import numpy as np
import time
import os
import urllib.request
import bz2
from scipy.spatial import distance as dist
from assistant.core.event_bus import bus, EventType
from assistant.core.mouth import speak, stop_llm_speech

LANDMARKS_URL = "https://github.com/davisking/dlib-models/raw/master/shape_predictor_68_face_landmarks.dat.bz2"
LANDMARKS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "shape_predictor_68_face_landmarks.dat")

def download_landmarks():
    """Downloads and extracts the dlib 68 point facial landmarks model if missing."""
    if not os.path.exists(LANDMARKS_FILE):
        os.makedirs(os.path.dirname(LANDMARKS_FILE), exist_ok=True)
        bus.emit(EventType.AUTH_STATUS, {"status": "Downloading face landmark models..."})
        try:
            print("Downloading shape_predictor_68_face_landmarks.dat.bz2...")
            temp_bz2 = LANDMARKS_FILE + ".bz2"
            urllib.request.urlretrieve(LANDMARKS_URL, temp_bz2)
            print("Extracting...")
            with bz2.BZ2File(temp_bz2, 'rb') as source, open(LANDMARKS_FILE, 'wb') as target:
                target.write(source.read())
            os.remove(temp_bz2)
            print("Download and extraction complete.")
        except Exception as e:
            print(f"Error downloading landmarks: {e}")
            return False
    return True

def eye_aspect_ratio(eye):
    """Calculate the Eye Aspect Ratio (EAR) for blink detection."""
    # Compute the euclidean distances between the two sets of vertical eye landmarks
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    # Compute the euclidean distance between the horizontal eye landmark
    C = dist.euclidean(eye[0], eye[3])
    # Compute the eye aspect ratio
    ear = (A + B) / (2.0 * C)
    return ear

def authenticate_user() -> bool:
    """
    Captures webcam feed, resizes frames for 4x speedup, flushes video buffer,
    and runs biometric matching and blink detection in parallel for security.
    Allows 5 attempts before exiting.
    """
    import dlib
    
    reference_image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "images", "owner.jpg")
    reference_encoding_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "images", "owner_encoding.npy")
    
    if not download_landmarks():
        bus.emit(EventType.AUTH_STATUS, {"status": "ERROR: Could not load landmark models."})
        time.sleep(3)
        return False
        
    try:
        if os.path.exists(reference_encoding_path):
            ref_encoding = np.load(reference_encoding_path)
        else:
            if not os.path.exists(reference_image_path):
                bus.emit(EventType.AUTH_STATUS, {"status": "ERROR: data/images/owner.jpg NOT FOUND"})
                time.sleep(3)
                return False
                
            ref_img = face_recognition.load_image_file(reference_image_path)
            ref_encodings = face_recognition.face_encodings(ref_img)
            if not ref_encodings:
                 bus.emit(EventType.AUTH_STATUS, {"status": "ERROR: NO FACE DETECTED IN owner.jpg"})
                 time.sleep(3)
                 return False
            ref_encoding = ref_encodings[0]
            np.save(reference_encoding_path, ref_encoding)
    except Exception as e:
        print(f"Auth init error: {e}")
        return False

    predictor = dlib.shape_predictor(LANDMARKS_FILE)
    
    # Indices for eyes in the 68-point model
    (lStart, lEnd) = (42, 48)
    (rStart, rEnd) = (36, 42)
    
    EAR_THRESHOLD = 0.21
    EAR_CONSEC_FRAMES = 2
    
    stop_llm_speech()
    speak("Initializing biometric scanner.", message_id="AUTH_HIDDEN")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        bus.emit(EventType.AUTH_STATUS, {"status": "ERROR: CAMERA NOT FOUND"})
        speak("Could not open camera.", message_id="AUTH_HIDDEN")
        time.sleep(3)
        return False
        
    # Attempt to set buffer size to 1 to reduce lag (supported by some backends)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    for attempt in range(1, 6):
        stop_llm_speech()
        bus.emit(EventType.AUTH_STATUS, {"status": f"ATTEMPT {attempt}/5: SCANNING BIOMETRICS & LIVENESS"})
        speak("Biometric scan started. Please look at the camera and blink to verify.", message_id="AUTH_HIDDEN")
        from assistant.core.mouth import wait_for_tts_completion
        wait_for_tts_completion()
        
        blink_detected = False
        blink_counter = 0
        
        # Flush initial buffer lag
        for _ in range(10): 
            cap.grab()
            
        start_time = time.time()
        last_recognition_time = 0
        owner_verified_time = 0
        owner_face_loc = None
        
        # Keep checking for 10 seconds per attempt
        while time.time() - start_time < 10:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue
                
            # Downscale frame by 4x (fx=0.25, fy=0.25) to speed up processing by ~94%
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            small_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            small_gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            
            # Find all face locations on the downscaled frame (fast)
            face_locations = face_recognition.face_locations(small_rgb)
            if face_locations:
                current_time = time.time()
                
                # Limit face encoding/matching to once every 1.5s to prevent CPU congestion and Kokoro audio cracking
                if current_time - last_recognition_time > 1.5:
                    face_encodings = face_recognition.face_encodings(small_rgb, face_locations)
                    last_recognition_time = current_time
                    
                    # Check if any face matches the owner
                    owner_index = -1
                    for idx, face_encoding in enumerate(face_encodings):
                        matches = face_recognition.compare_faces([ref_encoding], face_encoding, tolerance=0.6)
                        if matches[0]:
                            owner_index = idx
                            break
                            
                    if owner_index != -1:
                        owner_verified_time = current_time
                        owner_face_loc = face_locations[owner_index]
                    else:
                        owner_face_loc = None
                else:
                    # In the 1.5s cooldown, if owner was verified recently, assume the detected face is the owner
                    if current_time - owner_verified_time < 2.0:
                        owner_face_loc = face_locations[0]
                    else:
                        owner_face_loc = None
                        
                if owner_face_loc:
                    # Check blink status on the owner's face location
                    top, right, bottom, left = owner_face_loc
                    rect = dlib.rectangle(left, top, right, bottom)
                    
                    shape = predictor(small_gray, rect)
                    shape = np.array([[p.x, p.y] for p in shape.parts()])
                    
                    leftEye = shape[lStart:lEnd]
                    rightEye = shape[rStart:rEnd]
                    leftEAR = eye_aspect_ratio(leftEye)
                    rightEAR = eye_aspect_ratio(rightEye)
                    
                    ear = (leftEAR + rightEAR) / 2.0
                    
                    if ear < EAR_THRESHOLD:
                        blink_counter += 1
                    else:
                        if blink_counter >= EAR_CONSEC_FRAMES:
                            blink_detected = True
                        blink_counter = 0
                        
                    if blink_detected:
                        break
            
            # Throttle the loop to prevent 100% CPU usage and allow TTS (Kokoro) to run smoothly
            time.sleep(0.03)
                        
        if blink_detected:
            stop_llm_speech()
            bus.emit(EventType.AUTH_STATUS, {"status": "BIOMETRIC MATCH & LIVENESS SUCCESSFUL. WELCOME BACK."})
            speak("Biometric match successful. Welcome back.", message_id="AUTH_HIDDEN")
            from assistant.core.mouth import wait_for_tts_completion
            wait_for_tts_completion()
            bus.emit(EventType.AUTH_SUCCESS, {})
            cap.release()
            return True
        else:
            bus.emit(EventType.AUTH_STATUS, {"status": f"ATTEMPT {attempt} FAILED: TIMEOUT OR NO MATCH"})
            stop_llm_speech()
            speak("Scan failed. Please look at the camera and blink.", message_id="AUTH_HIDDEN")
            from assistant.core.mouth import wait_for_tts_completion
            wait_for_tts_completion()
            
    cap.release()
    bus.emit(EventType.AUTH_FAILED, {})
    stop_llm_speech()
    speak("Authentication failed. Terminating.", message_id="AUTH_HIDDEN")
    time.sleep(2)
    return False
