import cv2
import socket
import json
import time
import random
import threading

# Connection to Java Command Center
JAVA_HOST = '127.0.0.1'
JAVA_PORT = 9090


def send_alert_to_java(alert_data):
    """Pushes JSON alerts directly to the Java TCP Server"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((JAVA_HOST, JAVA_PORT))
            # Send payload with newline so Java's readLine() captures it
            s.sendall((json.dumps(alert_data) + '\n').encode('utf-8'))
    except ConnectionRefusedError:
        print("[WARNING] Could not connect to Java Command Center. Is it running?")


def red_team_simulator():
    """Simulates unauthorized cyber attacks (Brute Force, Packet Sniffing)"""
    threats = ['Brute Force Login', 'Unauthorized API Access', 'Packet Interception']
    while True:
        time.sleep(random.randint(8, 20))  # Strike at random intervals
        alert = {
            "node_id": random.choice([1, 2]),
            "threat_type": random.choice(threats),
            "severity": "CRITICAL",
            "source_ip": f"10.0.0.{random.randint(1, 255)}"
        }
        print(f"[RED TEAM] Simulating attack: {alert['threat_type']}")
        send_alert_to_java(alert)


def video_processor():
    """Simulates physical surveillance using local webcam and OpenCV motion detection"""
    cap = cv2.VideoCapture(0)  # Change 0 to a video file path if you don't have a webcam

    if not cap.isOpened():
        print("[ERROR] Cannot access camera. Simulating motion events purely via text...")
        while True:
            time.sleep(15)
            send_alert_to_java({
                "node_id": 1, "threat_type": "Simulated Motion Detected",
                "severity": "MEDIUM", "source_ip": "192.168.1.101"
            })
        return

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()

    print("[WATCHTOWER] Camera active. Monitoring for physical anomalies...")

    while cap.isOpened():
        # Compute absolute difference between consecutive frames
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        for contour in contours:
            # Ignore small movements, only trigger on large movements (person walking)
            if cv2.contourArea(contour) > 8000:
                motion_detected = True
                break

        if motion_detected:
            alert = {
                "node_id": 1,
                "threat_type": "Physical Tampering / Motion Detected",
                "severity": "HIGH",
                "source_ip": "192.168.1.101"
            }
            print(f"[OPENCV ALERT] {alert['threat_type']}")
            send_alert_to_java(alert)
            time.sleep(5)  # 5-second cooldown to avoid spamming the logs

        frame1 = frame2
        ret, frame2 = cap.read()

        # Optional: Render view locally
        # cv2.imshow("Security Feed", frame1)
        # if cv2.waitKey(10) == 27: break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    print("--- Starting WATCHTOWER Analytics & Simulator ---")
    # Start the cyber attack simulator in a background thread
    threading.Thread(target=red_team_simulator, daemon=True).start()

    # Run video analytics on the main thread
    video_processor()