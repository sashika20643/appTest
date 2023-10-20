from flask import Flask, request, send_file,render_template
import os
import firebase_admin
from firebase_admin import credentials, storage
import cv2
from matplotlib import pyplot as plt
import mediapipe as mp
import numpy as np
import tensorflow as tf
import datetime


cred = credentials.Certificate("./social-lips-firebase-adminsdk-c28zn-d607a10c33.json")
firebase_admin.initialize_app(cred)

app = Flask(__name__)

# Function to download a video from Firebase Storage
def download_video(file_id, save_directory):
    bucket = firebase_admin.storage.bucket(app=firebase_admin.get_app(), name="social-lips.appspot.com")
    firebase_blob_path = "posts/video/" + file_id
    blob = bucket.blob(firebase_blob_path)
    file_name = os.path.basename(file_id)
    file_path = os.path.join(save_directory, file_name + ".mp4")
    blob.download_to_filename(file_path)
    print("file downloaded")
    return file_path

# Function to create a VTT subtitle file
def create_subtitle_file(video_file_path):
    subtitle_text = "WEBVTT\n\n0:00:00.000 --> 0:00:02.000\nSubtitle line 1\n\n0:00:02.001 --> 0:00:04.000\nSubtitle line 2"
    file_name = os.path.splitext(os.path.basename(video_file_path))[0]
    subtitle_file_path = "subtitle/" + file_name + ".vtt"
    with open(subtitle_file_path, "w", encoding="utf-8") as vtt_file:
        vtt_file.write(subtitle_text)
    print("Subtitle generated")
    return subtitle_file_path

# Function to upload a subtitle file to Firebase Storage
def upload_subtitle_to_firebase(subtitle_file_path, destination_blob_name):
    bucket = firebase_admin.storage.bucket(app=firebase_admin.get_app(), name="social-lips.appspot.com")
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(subtitle_file_path)
    print("Subtitle uploaded")
    return 1;
mp_holistic = mp.solutions.holistic # Holistic model
mp_drawing = mp.solutions.drawing_utils # Drawing utilities

def mediapipe_detection(image, model):
  image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # COLOR CONVERSION BGR 2 RGB
  image.flags.writeable = False                   # Image is no longer writeable
  results = model.process(image)                  # Make prediction
  image.flags.writeable = True                    # Image is now writeable
  image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)  # COLOR CONVERSION RGB 2 BGR
  return image, results
def draw_landmarks(image, results):
    mp_drawing.draw_landmarks(image, results.face_landmarks, mp_holistic.FACEMESH_TESSELATION) # Draw face connections
    mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS) # Draw pose connections
    mp_drawing.draw_landmarks(image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS) # Draw-left hand connections
    mp_drawing.draw_landmarks(image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS) #Draw right hand connections

def draw_styled_landmarks (image, results):
    #Draw face connections
    mp_drawing.draw_landmarks(image, results. face_landmarks, mp_holistic.FACEMESH_TESSELATION,
                              mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1),
                              mp_drawing.DrawingSpec(color=(80,256,121), thickness=1, circle_radius=1)
                             )
    # Draw pose connections
    mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS,
                              mp_drawing.DrawingSpec(color=(88,22,10), thickness=2, circle_radius=4),
                              mp_drawing.DrawingSpec (color=(80, 44, 121), thickness=2, circle_radius=2)
                             )
    #Draw Left hand connections
    mp_drawing.draw_landmarks (image, results. left_hand_landmarks, mp_holistic.HAND_CONNECTIONS,
                               mp_drawing.DrawingSpec(color=(121,22,76), thickness=2, circle_radius=4),
                               mp_drawing.DrawingSpec (color=(121,44,250), thickness=2, circle_radius=2) 
                              )
    #Draw right hand connections
    mp_drawing.draw_landmarks (image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS,
                               mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=4),
                               mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
                              )

def extract_keypoints(results):
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(132)
    face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(21*3)
    lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose, face, lh, rh])
    # Function to find the index of the first available camera
def find_available_camera():
    for i in range(10):  # Try the first 10 camera indices (adjust as needed)
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cap.release()  # Release the camera immediately
            return i
    return None  # No available cameras found


    
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download/<string:file_id>', methods=['GET'])
def download_file(file_id):

    try:
        save_directory = "videos/"
        video_file_path = download_video(file_id, save_directory)
        subtitle_file_path = create_subtitle_file(video_file_path)
        destination_blob_name = f"posts/subtitles/{os.path.basename(video_file_path)}.vtt"
        upload_subtitle_to_firebase(subtitle_file_path, destination_blob_name)
        
        # Clean up: Remove the local VTT and video files
        # os.remove(subtitle_file_path)
        # os.remove(video_file_path)

        return f"Subtitles uploaded to Firebase Storage as {destination_blob_name}"
    except Exception as e:
        return str(e), 404
    
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']

    if file.filename == '':
        return "No selected file", 400

    try:
        # Replace this with your Firebase Storage bucket name
        bucket = storage.bucket(app=firebase_admin.get_app(), name="social-lips.appspot.com")
        blob = bucket.blob(file.filename)

        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )

        return "File uploaded successfully"
    except Exception as e:
        return str(e), 500
@app.route('/model', methods=['GET'])
def model():
    # 1. New detection variables
    model = tf.keras.models.load_model('./Action.h5')
    actions = np.array(['hello', 'thanks', 'iloveyou'])
    sentence = []
    sequence = []
    predictions = []
    threshold = 0.7
    val = ''

    cap = cv2.VideoCapture('1.mp4')

    # Set mediopipe model
    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        while cap.isOpened():

            # Read feed
            ret, frame = cap.read()
            
            # Make detections
            if not ret:
                break  # End of video, break out of the loop

            #Make detections
            image, results = mediapipe_detection(frame, holistic)
    #         print(results)

            #Draw Landmarks
            draw_styled_landmarks(image, results)

            #2. Prediction Logic
            keypoints = extract_keypoints(results)
    #         sequence.insert(0,keypoints)
            sequence.append(keypoints)
            sequence = sequence[-29:]
    #         print(len(sequence))

            if len(sequence) == 29:
                res = model.predict(np.expand_dims(sequence, axis=0))[0]
                if (val != actions [np.argmax(res)]):
                    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    print(actions [np.argmax(res)])
                val = actions [np.argmax(res)]
                predictions.append(np.argmax(res))

            #3. Viz Logic
                if np.unique(predictions[-10:])[0]== np.argmax(res):
                    if res[np.argmax(res)] > threshold:
                        if len(sentence) > 0:
                            if actions[np.argmax(res)] != sentence[-1]:
                                sentence.append(actions[np.argmax(res)])
                        else:
                            sentence.append(actions[np.argmax(res)])
                if len(sentence) > 5:
                    sentence = sentence[-5:]
            
            cv2.rectangle(image, (0,0), (640, 40), (245, 117, 16), -1)
            cv2.putText(image,''.join(sentence), (3,30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

            # Show to screen
            cv2.imshow('OpenCV Feed', image)

            # Break gracefully
            if cv2.waitKey(10) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    
    app.run(host="127.0.0.1", port=8080, debug=True)
# [END gae_python3_app]
# [END gae_python38_app]
