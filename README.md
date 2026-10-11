# grueslesbox-w48

An interactive audio guestbook and jukebox project built into a vintage W48 Bakelite telephone (1950s). Powered by a Raspberry Pi Zero, custom audio hardware, Python state machine logic, and custom 3D-printed PETG mounts.

![Grueslesbox W48](assets/images/grueslesbox-w48.jpg)

---

## Features

- **Dual-Mode Operation:** 
  - **Record Mode (`record`):** Functions as a classic audio guestbook. Lifting the handset plays a welcome greeting (`greeting.wav`), followed by a beep (`beep.wav`), and then records the guest's message via the built-in electret microphone.
  - **Jukebox Mode (`playback`):** Acts as an interactive playback device. Lifting the handset continuously loops through all recorded guest messages, separated by a beep tone between tracks, allowing you to listen to all messages over and over again.
- **Hardware Hook Integration:** Direct control via the original mechanical hook switch using Raspberry Pi GPIO pins.
- **Clean Audio Architecture:** Designed with galvanic isolation components to prevent ground loops and humming noises.
- **Automated State Persistence:** Automatically tracks the current playback index (`playback_state.json`) for seamless continuous listening across sessions.

---

## Hardware & Components

- **Telephone:** Original W48 Bakelite telephone.
- **Microphone:** MCE-401 electret microphone capsule with a custom 3D-printed mount.
- **Controller:** Raspberry Pi Zero.
- **Audio Interface:** LogiLink UA0078 USB audio adapter.
- **Enclosure / Mounts:** Custom 3D-printed structural components (PETG).

---

## 3D Models & CAD Assets

The `assets/3d_models/` directory contains all custom-designed parts for 3D printing and modification:
- **`w48_raspberry_pi_mount` / `w48_pi_holder`:** Custom bracket for securing the Raspberry Pi inside the W48 shell (`.f3d`, `.stl`, `.3mf`).
- **`mce401_mic_mount`:** Specific capsule holder for the MCE-401 microphone (`.f3d`, `.stl`, `.3mf`).
- **`w48_usb_c`:** Custom mount/adapter elements (`.f3d`, `.stl`, `.3mf`).

---

## Project Structure

~/grueslesbox-w48/
├── audio/                   # Audio files (greeting.wav, beep.wav)
├── recordings/              # Recorded guest messages (.wav)
├── src/                     # Python controller scripts
├── assets/                  # Documentation, schematics, and 3D models
│   ├── images/              # Photos of the build and hardware
│   └── 3d_models/           # STL, 3MF, and Fusion 360 files
├── config.json              # Mode configuration (record / playback)
├── playback_state.json      # Persistent tracking for jukebox playback
└── README.md

---

## Configuration (`config.json`)

The operating mode of the phone can be configured via the `config.json` file in the root directory by setting the "mode" key to either "record" or "playback":

{
  "_comment": "Accepted values for 'mode': 'record' (recording mode) or 'playback' (jukebox playback mode)",
  "mode": "record"
}

---

## License

- **Software / Code:** 
  Licensed under the **Apache License 2.0**. You may use, modify, and distribute the code under the terms of this license.
- **Hardware & 3D Models (`assets/`):** 
  Licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)**. This applies to all 3D models (`.f3d`, `.stl`, `.3mf`), schematics, and images located in the `assets/` directory.