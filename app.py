import json
import time
import cv2
import customtkinter as ctk
import threading

from gesture_detector import HandDetector
from gesture_actions import GestureActions
from gui import GestureControllerGUI


class HandGestureController:

    def __init__(self):

        # ============================================================
        # LOAD CONFIG
        # ============================================================

        try:
            with open("config.json", "r") as file:
                self.config = json.load(file)

        except FileNotFoundError:
            print("Error: config.json not found.")
            raise

        # ============================================================
        # CAMERA SETTINGS
        # ============================================================

        camera_config = self.config.get("camera", {})

        self.camera_index = camera_config.get("camera_index", 0)
        self.frame_width = camera_config.get("frame_width", 640)
        self.frame_height = camera_config.get("frame_height", 480)

        # ============================================================
        # HAND DETECTION SETTINGS
        # ============================================================

        detection_config = self.config.get("hand_detection", {})

        self.detector = HandDetector(
            max_num_hands=detection_config.get("max_num_hands", 1),
            min_detection_confidence=detection_config.get(
                "min_detection_confidence", 0.7
            ),
            min_tracking_confidence=detection_config.get(
                "min_tracking_confidence", 0.7
            )
        )

        # ============================================================
        # ACTIONS
        # ============================================================

        self.actions = GestureActions()

        # ============================================================
        # APPLICATION STATE
        # ============================================================

        self.camera = None
        self.running = False

        # Background camera thread
        self.camera_thread = None

        # Lock for sharing camera frame safely
        self.data_lock = threading.Lock()

        # Latest processed frame
        self.latest_frame = None

        # Latest landmarks
        self.latest_landmarks = None

        # Latest gesture
        self.latest_gesture = "NONE"

        # ============================================================
        # CURSOR STATE
        # ============================================================

        self.smooth_x = None
        self.smooth_y = None

        # ------------------------------------------------------------
        # CURSOR SMOOTHING
        #
        # Smaller value = smoother and slower
        # ------------------------------------------------------------

        self.smoothing = 0.10

        # Ignore tiny cursor movements
        self.deadzone = 5

        # ------------------------------------------------------------
        # ACTIVE CAMERA AREA
        #
        # Instead of using complete camera area, we use the center
        # area. This makes cursor movement less sensitive.
        # ------------------------------------------------------------

        self.min_x = 0.15
        self.max_x = 0.85

        self.min_y = 0.15
        self.max_y = 0.85

        # ============================================================
        # PINCH SETTINGS
        # ============================================================

        self.pinch_threshold = 0.055

        self.index_pinch_active = False
        self.middle_pinch_active = False

        self.last_pinch_time = 0

        self.pinch_cooldown = 0.45

        # ============================================================
        # GUI
        # ============================================================

        self.root = ctk.CTk()

        self.gui = GestureControllerGUI(
            self.root,
            start_callback=self.start_controller,
            stop_callback=self.stop_controller
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close_application
        )

    # ================================================================
    # START CONTROLLER
    # ================================================================

    def start_controller(self):

        if self.running:
            return

        # ------------------------------------------------------------
        # OPEN CAMERA
        # ------------------------------------------------------------

        self.camera = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.camera.isOpened():

            self.camera = cv2.VideoCapture(
                self.camera_index
            )

        if not self.camera.isOpened():

            self.gui.set_status(
                "Camera could not be opened"
            )

            print("Error: Could not open camera.")
            return

        # ------------------------------------------------------------
        # CAMERA SETTINGS
        # ------------------------------------------------------------

        self.camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.frame_width
        )

        self.camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.frame_height
        )

        # Keep camera buffer small
        try:
            self.camera.set(
                cv2.CAP_PROP_BUFFERSIZE,
                1
            )
        except Exception:
            pass

        # ------------------------------------------------------------
        # RESET STATES
        # ------------------------------------------------------------

        self.smooth_x = None
        self.smooth_y = None

        self.index_pinch_active = False
        self.middle_pinch_active = False

        self.last_pinch_time = 0

        with self.data_lock:

            self.latest_frame = None
            self.latest_landmarks = None
            self.latest_gesture = "NONE"

        # ------------------------------------------------------------
        # START RUNNING
        # ------------------------------------------------------------

        self.running = True

        self.gui.set_status(
            "Controller Running"
        )

        # ------------------------------------------------------------
        # START BACKGROUND CAMERA THREAD
        # ------------------------------------------------------------

        self.camera_thread = threading.Thread(
            target=self.camera_worker,
            daemon=True
        )

        self.camera_thread.start()

        # ------------------------------------------------------------
        # START GUI UPDATE LOOP
        # ------------------------------------------------------------

        self.update_gui()

    # ================================================================
    # BACKGROUND CAMERA WORKER
    # ================================================================

    def camera_worker(self):

        while self.running:

            if self.camera is None:
                break

            # --------------------------------------------------------
            # READ FRAME
            # --------------------------------------------------------

            success, frame = self.camera.read()

            if not success:

                time.sleep(0.03)
                continue

            # --------------------------------------------------------
            # MIRROR CAMERA
            # --------------------------------------------------------

            frame = cv2.flip(
                frame,
                1
            )

            landmarks = None
            gesture = "NO HAND"

            # --------------------------------------------------------
            # HAND DETECTION
            # --------------------------------------------------------

            try:

                frame, result = self.detector.find_hands(
                    frame,
                    draw=True
                )

                landmarks = self.detector.get_landmarks(
                    result
                )

            except Exception as error:

                print(
                    "Detection Error:",
                    error
                )

                landmarks = None

            # --------------------------------------------------------
            # GESTURE PROCESSING
            # --------------------------------------------------------

            if landmarks is not None:

                try:

                    gesture = self.detect_gesture(
                        landmarks
                    )

                except Exception as error:

                    print(
                        "Gesture Error:",
                        error
                    )

                    gesture = "HAND DETECTED"

            else:

                gesture = "NO HAND"

            # --------------------------------------------------------
            # CURSOR MOVEMENT
            #
            # IMPORTANT:
            # ONLY "MOVE CURSOR" can move cursor.
            # --------------------------------------------------------

            if (
                landmarks is not None
                and gesture == "MOVE CURSOR"
            ):

                try:

                    index_tip = landmarks[8]

                    self.move_cursor(
                        index_tip
                    )

                except Exception as error:

                    print(
                        "Cursor Error:",
                        error
                    )

            # --------------------------------------------------------
            # DISPLAY GESTURE
            # --------------------------------------------------------

            if gesture == "MOVE CURSOR":

                display_text = "MOVE CURSOR"

            elif gesture == "NO HAND":

                display_text = "NO HAND"

            else:

                display_text = gesture

            # --------------------------------------------------------
            # DRAW GESTURE TEXT
            # --------------------------------------------------------

            if gesture == "NO HAND":

                cv2.putText(
                    frame,
                    "Gesture: NO HAND",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2
                )

            else:

                cv2.putText(
                    frame,
                    f"Gesture: {display_text}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2
                )

            # --------------------------------------------------------
            # SAVE LATEST FRAME SAFELY
            # --------------------------------------------------------

            with self.data_lock:

                self.latest_frame = frame
                self.latest_landmarks = landmarks
                self.latest_gesture = gesture

    # ================================================================
    # GUI UPDATE
    # ================================================================

    def update_gui(self):

        if not self.running:
            return

        # ------------------------------------------------------------
        # GET LATEST FRAME
        # ------------------------------------------------------------

        frame = None
        gesture = "NONE"

        with self.data_lock:

            if self.latest_frame is not None:

                frame = self.latest_frame.copy()

            gesture = self.latest_gesture

        # ------------------------------------------------------------
        # UPDATE GUI
        # ------------------------------------------------------------

        if frame is not None:

            try:

                self.gui.update_frame(
                    frame
                )

            except Exception as error:

                print(
                    "GUI Error:",
                    error
                )

        # ------------------------------------------------------------
        # CONTINUE GUI LOOP
        #
        # 15 ms ≈ 66 updates/second
        # ------------------------------------------------------------

        if self.running:

            self.root.after(
                15,
                self.update_gui
            )

    # ================================================================
    # DISTANCE BETWEEN TWO LANDMARKS
    # ================================================================

    def distance(
        self,
        point1,
        point2
    ):

        dx = point1.x - point2.x
        dy = point1.y - point2.y

        return (
            dx * dx
            + dy * dy
        ) ** 0.5

    # ================================================================
    # CHECK PINCH
    # ================================================================

    def is_pinch(
        self,
        finger_tip,
        thumb_tip
    ):

        distance = self.distance(
            finger_tip,
            thumb_tip
        )

        return distance < self.pinch_threshold

    # ================================================================
    # CHECK ONLY INDEX FINGER
    # ================================================================

    def is_index_only(
        self,
        landmarks
    ):

        if (
            landmarks is None
            or len(landmarks) < 21
        ):
            return False

        # ------------------------------------------------------------
        # INDEX
        # ------------------------------------------------------------

        index_tip = landmarks[8]
        index_pip = landmarks[6]

        # ------------------------------------------------------------
        # MIDDLE
        # ------------------------------------------------------------

        middle_tip = landmarks[12]
        middle_pip = landmarks[10]

        # ------------------------------------------------------------
        # RING
        # ------------------------------------------------------------

        ring_tip = landmarks[16]
        ring_pip = landmarks[14]

        # ------------------------------------------------------------
        # PINKY
        # ------------------------------------------------------------

        pinky_tip = landmarks[20]
        pinky_pip = landmarks[18]

        # ------------------------------------------------------------
        # CHECK FINGER POSITIONS
        # ------------------------------------------------------------

        index_up = (
            index_tip.y < index_pip.y
        )

        middle_down = (
            middle_tip.y > middle_pip.y
        )

        ring_down = (
            ring_tip.y > ring_pip.y
        )

        pinky_down = (
            pinky_tip.y > pinky_pip.y
        )

        return (
            index_up
            and middle_down
            and ring_down
            and pinky_down
        )

    # ================================================================
    # MOVE CURSOR
    # ================================================================

    def move_cursor(
        self,
        index_tip
    ):

        if index_tip is None:
            return

        # ------------------------------------------------------------
        # GET NORMALIZED INDEX POSITION
        # ------------------------------------------------------------

        x = max(
            0.0,
            min(
                1.0,
                index_tip.x
            )
        )

        y = max(
            0.0,
            min(
                1.0,
                index_tip.y
            )
        )

        # ------------------------------------------------------------
        # MAP CAMERA AREA TO SCREEN
        #
        # Only the center 70% of camera controls the screen.
        # This reduces sensitivity.
        # ------------------------------------------------------------

        x = (
            x - self.min_x
        ) / (
            self.max_x - self.min_x
        )

        y = (
            y - self.min_y
        ) / (
            self.max_y - self.min_y
        )

        # Keep inside screen range

        x = max(
            0.0,
            min(
                1.0,
                x
            )
        )

        y = max(
            0.0,
            min(
                1.0,
                y
            )
        )

        # ------------------------------------------------------------
        # SCREEN COORDINATES
        # ------------------------------------------------------------

        screen_x = int(
            x * (
                self.actions.screen_width - 1
            )
        )

        screen_y = int(
            y * (
                self.actions.screen_height - 1
            )
        )

        # ------------------------------------------------------------
        # FIRST POSITION
        # ------------------------------------------------------------

        if (
            self.smooth_x is None
            or self.smooth_y is None
        ):

            self.smooth_x = screen_x
            self.smooth_y = screen_y

            return

        # ------------------------------------------------------------
        # EXPONENTIAL SMOOTHING
        #
        # This strongly reduces jitter.
        # ------------------------------------------------------------

        new_x = (
            self.smooth_x
            + self.smoothing
            * (
                screen_x
                - self.smooth_x
            )
        )

        new_y = (
            self.smooth_y
            + self.smoothing
            * (
                screen_y
                - self.smooth_y
            )
        )

        # ------------------------------------------------------------
        # DEADZONE
        #
        # Ignore very small movements.
        # ------------------------------------------------------------

        if (
            abs(
                new_x
                - self.smooth_x
            )
            >= self.deadzone
        ):

            self.smooth_x = new_x

        if (
            abs(
                new_y
                - self.smooth_y
            )
            >= self.deadzone
        ):

            self.smooth_y = new_y

        # ------------------------------------------------------------
        # MOVE REAL CURSOR
        # ------------------------------------------------------------

        try:

            self.actions.move_mouse(
                int(self.smooth_x),
                int(self.smooth_y)
            )

        except Exception:

            pass

    # ================================================================
    # DETECT GESTURE
    # ================================================================

    def detect_gesture(
        self,
        landmarks
    ):

        if (
            landmarks is None
            or len(landmarks) < 21
        ):

            return "NO HAND"

        # ------------------------------------------------------------
        # LANDMARKS
        # ------------------------------------------------------------

        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]

        # ------------------------------------------------------------
        # PINCH CHECK
        # ------------------------------------------------------------

        index_pinch = self.is_pinch(
            index_tip,
            thumb_tip
        )

        middle_pinch = self.is_pinch(
            middle_tip,
            thumb_tip
        )

        current_time = time.time()

        # ============================================================
        # INDEX + THUMB
        # SINGLE CLICK
        # ============================================================

        if (
            index_pinch
            and not middle_pinch
        ):

            if (
                not self.index_pinch_active
                and (
                    current_time
                    - self.last_pinch_time
                    > self.pinch_cooldown
                )
            ):

                self.index_pinch_active = True

                self.last_pinch_time = (
                    current_time
                )

                self.actions.left_click()

                # Lock cursor
                self.smooth_x = None
                self.smooth_y = None

                return (
                    "INDEX + THUMB PINCH - SINGLE CLICK"
                )

            return "INDEX + THUMB PINCH"

        else:

            self.index_pinch_active = False

        # ============================================================
        # MIDDLE + THUMB
        # DOUBLE CLICK
        # ============================================================

        if (
            middle_pinch
            and not index_pinch
        ):

            if (
                not self.middle_pinch_active
                and (
                    current_time
                    - self.last_pinch_time
                    > self.pinch_cooldown
                )
            ):

                self.middle_pinch_active = True

                self.last_pinch_time = (
                    current_time
                )

                self.actions.double_click()

                # Lock cursor
                self.smooth_x = None
                self.smooth_y = None

                return (
                    "MIDDLE + THUMB PINCH - DOUBLE CLICK"
                )

            return "MIDDLE + THUMB PINCH"

        else:

            self.middle_pinch_active = False

        # ============================================================
        # ONLY INDEX FINGER
        # CURSOR MOVEMENT
        # ============================================================

        if self.is_index_only(
            landmarks
        ):

            return "MOVE CURSOR"

        # ============================================================
        # EVERYTHING ELSE
        # CURSOR LOCKED
        # ============================================================

        return "HAND DETECTED - CURSOR LOCKED"

    # ================================================================
    # STOP CONTROLLER
    # ================================================================

    def stop_controller(self):

        self.running = False

        # ------------------------------------------------------------
        # RELEASE CAMERA
        # ------------------------------------------------------------

        if self.camera is not None:

            try:

                self.camera.release()

            except Exception:

                pass

            self.camera = None

        # ------------------------------------------------------------
        # RESET STATES
        # ------------------------------------------------------------

        self.index_pinch_active = False
        self.middle_pinch_active = False

        self.smooth_x = None
        self.smooth_y = None

        with self.data_lock:

            self.latest_frame = None
            self.latest_landmarks = None
            self.latest_gesture = "NONE"

        self.gui.set_status(
            "Controller Stopped"
        )

    # ================================================================
    # CLOSE APPLICATION
    # ================================================================

    def close_application(self):

        self.running = False

        # ------------------------------------------------------------
        # RELEASE CAMERA
        # ------------------------------------------------------------

        if self.camera is not None:

            try:

                self.camera.release()

            except Exception:

                pass

            self.camera = None

        # ------------------------------------------------------------
        # CLOSE DETECTOR
        # ------------------------------------------------------------

        try:

            self.detector.close()

        except Exception:

            pass

        # ------------------------------------------------------------
        # EMERGENCY STOP
        # ------------------------------------------------------------

        try:

            self.actions.emergency_stop()

        except Exception:

            pass

        # ------------------------------------------------------------
        # CLOSE GUI
        # ------------------------------------------------------------

        try:

            self.root.destroy()

        except Exception:

            pass

    # ================================================================
    # RUN
    # ================================================================

    def run(self):

        self.root.mainloop()


# ====================================================================
# MAIN
# ====================================================================

if __name__ == "__main__":

    app = HandGestureController()

    try:

        app.run()

    except KeyboardInterrupt:

        app.close_application()

    except Exception as error:

        print(
            "\nApplication Error:"
        )

        print(error)

        try:

            app.close_application()

        except Exception:

            pass