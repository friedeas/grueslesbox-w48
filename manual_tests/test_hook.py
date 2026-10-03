#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO

# --- PIN CONFIGURATION ---
HOOK_PIN = 18  # GPIO 18 (Physical Pin 12) for the hook switch
# -------------------------

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Configure hook switch as input with internal pull-up resistor.
    # (Expects the switch to pull the pin to GND when picked up).
    GPIO.setup(HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def main():
    setup_gpio()
    print("--- W48 Hook Switch Test ---")
    print(f"Monitoring GPIO {HOOK_PIN} (Physical Pin 12)...")
    print("Pick up and hang up the handset to test.")
    print("Press CTRL+C to exit.\n")

    try:
        last_state = None
        while True:
            hook_state = GPIO.input(HOOK_PIN)
            
            if hook_state != last_state:
                if hook_state == GPIO.LOW:
                    print("[Status] Handset OFF-HOOK (Picked up)")
                else:
                    print("[Status] Handset ON-HOOK (Placed down)")
                last_state = hook_state
                
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nTest terminated.")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()