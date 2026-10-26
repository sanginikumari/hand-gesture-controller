import os
import cv2
import mediapipe as mp


class HandDetector:
    def __init__(
        self,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    ):
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

        # Path of the MediaPipe hand model
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(
            base_dir,
            "models",
            "hand_landmarker.task"
        )

        # Check whether model exists
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Hand model not found:\n{self.model_path}"
            )

        # MediaPipe Tasks API
        self.base_options = mp.tasks.BaseOptions
        self.vision = mp.tasks.vision

        # Configure Hand Landmarker
        options = self.vision.HandLandmarkerOptions(
            base_options=self.base_options(
                model_asset_path=self.model_path
            ),
            running_mode=self.vision.RunningMode.IMAGE,
            num_hands=self.max_num_hands,
            min_hand_detection_confidence=self.min_detection_confidence,
            min_hand_presence_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence
        )

        # Create detector
        self.detector = self.vision.HandLandmarker.create_from_options(
            options
        )

    def find_hands(self, frame, draw=True):
        """
        Detect hands in an OpenCV BGR frame.

        Returns:
            frame: processed OpenCV frame
            result: MediaPipe hand detection result
        """

        # OpenCV uses BGR, MediaPipe expects RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create MediaPipe image
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        # Detect hands
        result = self.detector.detect(mp_image)

        # Draw landmarks
        if draw and result.hand_landmarks:
            height, width, _ = frame.shape

            for hand_landmarks in result.hand_landmarks:

                # Draw connections
                for connection in mp.tasks.vision.HandLandmarksConnections.HAND_CONNECTIONS:
                    start = hand_landmarks[connection.start]
                    end = hand_landmarks[connection.end]

                    start_point = (
                        int(start.x * width),
                        int(start.y * height)
                    )

                    end_point = (
                        int(end.x * width),
                        int(end.y * height)
                    )

                    cv2.line(
                        frame,
                        start_point,
                        end_point,
                        (0, 255, 0),
                        2
                    )

                # Draw landmark points
                for landmark in hand_landmarks:
                    x = int(landmark.x * width)
                    y = int(landmark.y * height)

                    cv2.circle(
                        frame,
                        (x, y),
                        5,
                        (255, 0, 0),
                        -1
                    )

        return frame, result

    def get_landmarks(self, result):
        """
        Return the landmarks of the first detected hand.
        """

        if result is None:
            return None

        if not result.hand_landmarks:
            return None

        return result.hand_landmarks[0]

    def close(self):
        """Close the MediaPipe detector safely."""

        if self.detector is not None:
            self.detector.close()
            self.detector = None