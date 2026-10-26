import time
import pyautogui

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL

    VOLUME_CONTROL_AVAILABLE = True

except ImportError:
    VOLUME_CONTROL_AVAILABLE = False


# PyAutoGUI ko unnecessary delay na dene ke liye
pyautogui.PAUSE = 0


class GestureActions:

    def __init__(self):
        # Screen size
        self.screen_width, self.screen_height = pyautogui.size()

        # Action cooldowns
        self.last_action_time = {}
        self.cooldown = 0.5

        # Volume control
        self.volume = None

        if VOLUME_CONTROL_AVAILABLE:
            try:
                devices = AudioUtilities.GetSpeakers()

                interface = devices.Activate(
                    IAudioEndpointVolume._iid_,
                    CLSCTX_ALL,
                    None
                )

                self.volume = interface.QueryInterface(
                    IAudioEndpointVolume
                )

            except Exception:
                self.volume = None

    # --------------------------------------------------
    # COOLDOWN
    # --------------------------------------------------

    def _can_perform(self, action_name):

        current_time = time.time()

        last_time = self.last_action_time.get(
            action_name,
            0
        )

        if current_time - last_time >= self.cooldown:

            self.last_action_time[action_name] = current_time

            return True

        return False

    # --------------------------------------------------
    # MOUSE MOVEMENT
    # --------------------------------------------------

    def move_mouse(self, x, y):

        try:

            # x and y are ALREADY screen coordinates.
            # No extra mapping or smoothing here.
            # Cursor smoothing is handled in app.py.

            x = int(
                max(
                    0,
                    min(
                        x,
                        self.screen_width - 1
                    )
                )
            )

            y = int(
                max(
                    0,
                    min(
                        y,
                        self.screen_height - 1
                    )
                )
            )

            pyautogui.moveTo(
                x,
                y,
                duration=0
            )

        except Exception:
            pass

    # --------------------------------------------------
    # LEFT CLICK
    # --------------------------------------------------

    def left_click(self):

        if self._can_perform("left_click"):

            pyautogui.click()

    # --------------------------------------------------
    # RIGHT CLICK
    # --------------------------------------------------

    def right_click(self):

        if self._can_perform("right_click"):

            pyautogui.rightClick()

    # --------------------------------------------------
    # DOUBLE CLICK
    # --------------------------------------------------

    def double_click(self):

        if self._can_perform("double_click"):

            pyautogui.doubleClick(
                interval=0.08
            )

    # --------------------------------------------------
    # SCROLL
    # --------------------------------------------------

    def scroll_up(self):

        if self._can_perform("scroll_up"):

            pyautogui.scroll(5)

    def scroll_down(self):

        if self._can_perform("scroll_down"):

            pyautogui.scroll(-5)

    # --------------------------------------------------
    # VOLUME UP
    # --------------------------------------------------

    def volume_up(self):

        if not self._can_perform("volume_up"):
            return

        if self.volume is not None:

            try:

                current_volume = (
                    self.volume.GetMasterVolumeLevelScalar()
                )

                new_volume = min(
                    1.0,
                    current_volume + 0.05
                )

                self.volume.SetMasterVolumeLevelScalar(
                    new_volume,
                    None
                )

            except Exception:
                pass

    # --------------------------------------------------
    # VOLUME DOWN
    # --------------------------------------------------

    def volume_down(self):

        if not self._can_perform("volume_down"):
            return

        if self.volume is not None:

            try:

                current_volume = (
                    self.volume.GetMasterVolumeLevelScalar()
                )

                new_volume = max(
                    0.0,
                    current_volume - 0.05
                )

                self.volume.SetMasterVolumeLevelScalar(
                    new_volume,
                    None
                )

            except Exception:
                pass

    # --------------------------------------------------
    # MUTE / UNMUTE
    # --------------------------------------------------

    def mute_unmute(self):

        if not self._can_perform("mute_unmute"):
            return

        if self.volume is not None:

            try:

                current_state = self.volume.GetMute()

                self.volume.SetMute(
                    not current_state,
                    None
                )

            except Exception:
                pass

    # --------------------------------------------------
    # MEDIA CONTROL
    # --------------------------------------------------

    def play_pause(self):

        if self._can_perform("play_pause"):

            pyautogui.press("playpause")

    def next_track(self):

        if self._can_perform("next_track"):

            pyautogui.press("nexttrack")

    def previous_track(self):

        if self._can_perform("previous_track"):

            pyautogui.press("prevtrack")

    # --------------------------------------------------
    # EMERGENCY STOP
    # --------------------------------------------------

    def emergency_stop(self):

        try:

            pyautogui.moveTo(
                0,
                0,
                duration=0
            )

        except Exception:
            pass