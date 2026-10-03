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


class PhoneStateMachine(StateMachine):
    """State machine for the W48 audio guestbook."""

    # Define states
    idle = State(initial=True)
    greeting = State()
    recording = State()

    # Define transitions (allowing pick_up from greeting as well to prevent errors on rapid toggle)
    pick_up = idle.to(greeting) | greeting.to(greeting) | recording.to(greeting)
    start_recording = greeting.to(recording)
    hang_up = recording.to(idle) | greeting.to(idle) | idle.to(idle)

    def __init__(self, *args, **kwargs):
        self.current_process = None
        self.current_recording_file = None
        self.playback_stop_event = threading.Event()
        self.playback_thread = None
        super().__init__(*args, **kwargs)

    def _stop_current_process(self):
        """Immediately stops any running audio playback or recording process cleanly."""
        # Signal the playback thread to stop if active
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

        # Explicitly pass the sound card device (-D plughw:1,0) just like arecord
        self.current_process = subprocess.Popen(
            ["aplay", "-D", "plughw:1,0", str(filepath)], 
            stderr=subprocess.DEVNULL
        )

        # Wait for either the process to finish OR the stop event to be triggered by a hang-up.
        while self.current_process and self.current_process.poll() is None:
            if self.playback_stop_event.wait(timeout=0.1):
                self._stop_current_process()
                return False

        return self.current_state == self.greeting

    def on_enter_greeting(self):
        logger.info(f"State: GREETING (Handset lifted, playing greeting from {GREETING_FILE})")
        self.playback_stop_event.clear()

        def run_greeting_sequence():
            try:
                # Play greeting audio
                if not self._play_audio_blocking(GREETING_FILE):
                    return

                # Play beep tone if file exists
                if BEEP_FILE.exists() and self.current_state == self.greeting:
                    if not self._play_audio_blocking(BEEP_FILE):
                        return

                # If still in greeting state after playback finishes, transition to recording
                if self.current_state == self.greeting:
                    self.start_recording()

            except Exception as e:
                logger.error(f"Error during greeting phase: {e}")
                self.hang_up()

        # Run the playback sequence in a background thread so the GPIO event handler remains instantly responsive
        self.playback_thread = threading.Thread(target=run_greeting_sequence)
        self.playback_thread.start()

    def on_enter_recording(self):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.current_recording_file = RECORDINGS_DIR / f"recording_{timestamp}.wav"
        logger.info(f"State: RECORDING (Saving to: {self.current_recording_file})")

        try:
            # Start audio recording
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

    # GPIO Setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(LED_PIN, GPIO.OUT)
    
    # Turn on the green LED to indicate the program has successfully started
    GPIO.output(LED_PIN, GPIO.HIGH)

    box = PhoneStateMachine()

    # Initialize hook switch event listener (using both edges with bouncetime)
    GPIO.add_event_detect(
        HOOK_PIN, 
        GPIO.BOTH, 
        callback=lambda channel: handle_hook_state_change(channel, box), 
        bouncetime=200
    )

    try:
        # Keep the main thread alive while events handle the state machine
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