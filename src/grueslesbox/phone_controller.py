import json
import logging
from pathlib import Path
import subprocess
import threading
import time
import RPi.GPIO as GPIO
from statemachine import State, StateMachine

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("grueslesbox")

# GPIO Pin definitions
HOOK_PIN = 18  # Hook switch (Active LOW)
LED_PIN = 17   # Status LED

# Audio file paths (pointing to grueslesbox-w48/audio/)
BASE_DIR = Path.home() / "grueslesbox-w48"
AUDIO_DIR = BASE_DIR / "audio"
GREETING_FILE = AUDIO_DIR / "greeting.wav"
BEEP_FILE = AUDIO_DIR / "beep.wav"

RECORDINGS_DIR = BASE_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# Configuration & State tracking files
CONFIG_FILE = BASE_DIR / "config.json"
STATE_FILE = BASE_DIR / "playback_state.json"


def get_current_mode():
    """Reads the mode from config.json, fallback is 'record'."""
    if not CONFIG_FILE.exists():
        return "record"
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("mode", "record")
    except Exception as e:
        logger.warning(f"Failed to read config.json, falling back to 'record': {e}")
        return "record"


def get_next_recording_index(total_files):
    """Loads current playback index, calculates next with automatic wrap-around, saves state, and returns current."""
    index = 0
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                index = data.get("last_index", 0)
        except Exception:
            index = 0
    
    # Ensure index is within valid bounds
    if total_files > 0:
        if index >= total_files:
            index = 0
        next_index = (index + 1) % total_files
    else:
        next_index = 0
    
    # Save next state
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"last_index": next_index}, f)
    except Exception as e:
        logger.error(f"Failed to save playback state: {e}")
        
    return index


class PhoneStateMachine(StateMachine):
    """State machine for the W48 audio guestbook / jukebox."""

    # Define states
    idle = State(initial=True)
    greeting = State()
    recording = State()
    playback = State()

    # Define transitions
    pick_up = idle.to(greeting) | greeting.to(greeting) | recording.to(greeting) | playback.to(greeting)
    start_recording = greeting.to(recording)
    start_playback = greeting.to(playback)
    hang_up = recording.to(idle) | greeting.to(idle) | playback.to(idle) | idle.to(idle)

    def __init__(self, *args, **kwargs):
        self.current_process = None
        self.current_recording_file = None
        self.playback_stop_event = threading.Event()
        self.playback_thread = None
        super().__init__(*args, **kwargs)

    def _stop_current_process(self):
        """Immediately stops any running audio playback or recording process cleanly."""
        self.playback_stop_event.set()

        proc = self.current_process
        self.current_process = None  # Clear reference immediately to avoid race conditions

        if proc:
            try:
                if proc.poll() is None:
                    logger.info("Stopping active audio/recording process...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                
                if proc.stderr:
                    proc.stderr.close()
                if proc.stdout:
                    proc.stdout.close()
            except Exception as e:
                logger.debug(f"Error while cleaning up process: {e}")

    def on_enter_idle(self):
        logger.info("State: IDLE (Waiting for handset to be lifted)")
        GPIO.output(LED_PIN, GPIO.HIGH)
        self._stop_current_process()

    def _play_audio_blocking(self, filepath):
        """Plays an audio file asynchronously while monitoring the stop event without polling."""
        if not filepath.exists():
            return True

        self.current_process = subprocess.Popen(
            ["aplay", "-D", "plughw:1,0", str(filepath)], 
            stderr=subprocess.DEVNULL
        )

        while self.current_process and self.current_process.poll() is None:
            if self.playback_stop_event.wait(timeout=0.1):
                self._stop_current_process()
                return False

        return True

    def on_enter_greeting(self):
        mode = get_current_mode()
        logger.info(f"State: GREETING (Handset lifted, active mode: '{mode}')")
        self.playback_stop_event.clear()

        def run_sequence():
            try:
                if mode == "playback":
                    if self.current_state == self.greeting:
                        self.start_playback()
                else:
                    if not self._play_audio_blocking(GREETING_FILE):
                        return

                    if BEEP_FILE.exists() and self.current_state == self.greeting:
                        if not self._play_audio_blocking(BEEP_FILE):
                            return

                    if self.current_state == self.greeting:
                        self.start_recording()

            except Exception as e:
                logger.error(f"Error during greeting sequence: {e}")
                self.hang_up()

        self.playback_thread = threading.Thread(target=run_sequence)
        self.playback_thread.start()

    def on_enter_playback(self):
        logger.info("State: PLAYBACK (Starting continuous message playback)")
        self.playback_stop_event.clear()

        def run_playback_sequence():
            try:
                recordings = sorted(list(RECORDINGS_DIR.glob("*.wav")))
                if not recordings:
                    logger.info("No recordings found to play back.")
                    return

                is_first_in_session = True

                # Loop continuously as long as the handset remains lifted (in playback state)
                while self.current_state == self.playback:
                    file_index = get_next_recording_index(len(recordings))

                    # Play beep tone between messages (not for the very first file of this session)
                    if not is_first_in_session and BEEP_FILE.exists():
                        if not self._play_audio_blocking(BEEP_FILE):
                            break

                    current_file = recordings[file_index]
                    logger.info(f"Playing message {file_index + 1} of {len(recordings)}: {current_file.name}")

                    if not self._play_audio_blocking(current_file):
                        break

                    is_first_in_session = False
                    
                    # Small pause between messages if desired, or let it flow directly
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error during playback sequence: {e}")
            finally:
                if self.current_state == self.playback:
                    self.hang_up()

        self.playback_thread = threading.Thread(target=run_playback_sequence)
        self.playback_thread.start()

    def on_enter_recording(self):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.current_recording_file = RECORDINGS_DIR / f"recording_{timestamp}.wav"
        logger.info(f"State: RECORDING (Saving to: {self.current_recording_file.name})")

        try:
            self.current_process = subprocess.Popen([
                "arecord",
                "-D", "plughw:1,0",
                "-r", "16000",
                "-f", "S16_LE",
                "-c", "1",
                str(self.current_recording_file)
            ], stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")


def handle_hook_state_change(channel, box):
    """Event callback triggered on hook switch state change."""
    current_state = GPIO.input(HOOK_PIN)
    
    if current_state == GPIO.LOW:
        logger.info("Hook switch event: Handset lifted.")
        box.pick_up()
    else:
        logger.info("Hook switch event: Handset replaced.")
        box.hang_up()


def main():
    logger.info("Starting Grueslesbox W48 controller...")
    
    # Log the currently active mode right at startup
    active_mode = get_current_mode()
    logger.info(f"Configuration loaded -> Active mode: '{active_mode}'")

    # GPIO Setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(LED_PIN, GPIO.OUT)
    
    GPIO.output(LED_PIN, GPIO.HIGH)

    box = PhoneStateMachine()

    GPIO.add_event_detect(
        HOOK_PIN, 
        GPIO.BOTH, 
        callback=lambda channel: handle_hook_state_change(channel, box), 
        bouncetime=200
    )

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Program interrupted by user (KeyboardInterrupt).")
    finally:
        box._stop_current_process()
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()
        logger.info("GPIO cleaned up. Program exited.")


if __name__ == "__main__":
    main()