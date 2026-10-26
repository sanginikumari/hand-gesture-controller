import customtkinter as ctk
import cv2
from PIL import Image, ImageTk


class GestureControllerGUI:
    def __init__(self, root, start_callback, stop_callback):
        self.root = root
        self.start_callback = start_callback
        self.stop_callback = stop_callback

        self.root.title("Hand Gesture Controller")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.camera_running = False
        self.current_frame = None
        self.video_label = None

        self.create_interface()

    def create_interface(self):
        # Main heading
        self.title_label = ctk.CTkLabel(
            self.root,
            text="🖐 Hand Gesture Controller",
            font=ctk.CTkFont(size=30, weight="bold")
        )
        self.title_label.pack(pady=(25, 5))

        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            self.root,
            text="Control your computer using hand gestures",
            font=ctk.CTkFont(size=16)
        )
        self.subtitle_label.pack(pady=(0, 20))

        # Video frame
        self.video_frame = ctk.CTkFrame(
            self.root,
            corner_radius=15
        )
        self.video_frame.pack(
            padx=30,
            pady=10,
            fill="both",
            expand=True
        )

        self.video_label = ctk.CTkLabel(
            self.video_frame,
            text="Camera is currently stopped",
            font=ctk.CTkFont(size=20)
        )
        self.video_label.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        # Status
        self.status_label = ctk.CTkLabel(
            self.root,
            text="● Status: Stopped",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.status_label.pack(pady=(15, 10))

        # Buttons frame
        self.button_frame = ctk.CTkFrame(
            self.root,
            fg_color="transparent"
        )
        self.button_frame.pack(pady=(5, 25))

        self.start_button = ctk.CTkButton(
            self.button_frame,
            text="▶ Start Controller",
            width=180,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.start_controller
        )
        self.start_button.grid(
            row=0,
            column=0,
            padx=10
        )

        self.stop_button = ctk.CTkButton(
            self.button_frame,
            text="■ Stop Controller",
            width=180,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.stop_controller,
            state="disabled"
        )
        self.stop_button.grid(
            row=0,
            column=1,
            padx=10
        )

        self.exit_button = ctk.CTkButton(
            self.button_frame,
            text="✕ Exit",
            width=120,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.close
        )
        self.exit_button.grid(
            row=0,
            column=2,
            padx=10
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )

    def start_controller(self):
        self.camera_running = True

        self.start_button.configure(
            state="disabled"
        )

        self.stop_button.configure(
            state="normal"
        )

        self.status_label.configure(
            text="● Status: Running"
        )

        if self.start_callback:
            self.start_callback()

    def stop_controller(self):
        self.camera_running = False

        self.start_button.configure(
            state="normal"
        )

        self.stop_button.configure(
            state="disabled"
        )

        self.status_label.configure(
            text="● Status: Stopped"
        )

        if self.stop_callback:
            self.stop_callback()

        self.video_label.configure(
            image=None,
            text="Camera is currently stopped"
        )

    def update_frame(self, frame):
        """
        Display an OpenCV frame inside the GUI.
        """

        if frame is None:
            return

        self.current_frame = frame.copy()

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        image = Image.fromarray(frame_rgb)

        # Fit the camera image into the GUI.
        image.thumbnail((850, 480))

        photo = ImageTk.PhotoImage(image)

        self.video_label.configure(
            image=photo,
            text=""
        )

        self.video_label.image = photo

    def set_status(self, message):
        """
        Update the status text.
        """

        self.status_label.configure(
            text=f"● Status: {message}"
        )

    def close(self):
        """
        Close the GUI safely.
        """

        try:
            if self.stop_callback:
                self.stop_callback()
        except Exception:
            pass

        self.root.destroy()