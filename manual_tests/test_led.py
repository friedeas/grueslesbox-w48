#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO

# --- PIN CONFIGURATION ---
LED_PIN = 17  # GPIO 17 (Physical Pin 11) for the green LED
# -------------------------

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Configure LED pin as output
    GPIO.setup(LED_PIN, GPIO.OUT)

def main():
    setup_gpio()
    print("--- W48 LED Slow Blink Test ---")
    print(f"Blinking green LED on GPIO {LED_PIN} (Physical Pin 11)...")
    print("Press CTRL+C to exit.\n")

    try:
        while True:
            # Turn LED ON
            GPIO.output(LED_PIN, GPIO.HIGH)
            print("[Status] LED ON")
            time.sleep(1.0)  # Stay on for 1 second
            
            # Turn LED OFF
            GPIO.output(LED_PIN, GPIO.LOW)
            print("[Status] LED OFF")
            time.sleep(1.0)  # Stay off for 1 second

    except KeyboardInterrupt:
        print("\nTest terminated.")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up safely.")

if __name__ == "__main__":
    main()