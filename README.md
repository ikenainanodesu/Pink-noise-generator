[简体中文](./README.CN.md) | [English](./README.md)

# SMPTE ST 2095-1 Pink Noise Generator (with GUI)

This tool generates **Band-Limited Pink Noise** compliant with the **SMPTE ST 2095-1** standard. It consists of a core algorithm script and a user-friendly Graphical User Interface (GUI), designed for audio engineers and acoustic calibration.

## 📂 File Structure

Ensure both files are located in the same directory:

1.  **`smpte_noise.py`**: The core algorithm script (Original SMPTE code).
2.  **`gui_generator.py`**: The GUI launcher (Run this file).

---

## 🧠 Algorithm Principle (SMPTE ST 2095-1)

This tool strictly adheres to the **SMPTE ST 2095-1:2015** standard (and its 2022 revision). Pink noise is a random signal with equal energy per octave (power spectral density is inversely proportional to the frequency, $1/f$).

### Core Implementation Details:

1.  **Pseudo-Random Number Generator (PRNG)**:
    Uses a Linear Congruential Generator (LCG) to produce high-quality white noise as the source signal.

2.  **Pink Filter Network**:
    The white noise is processed through a parallel network of **6 first-order low-pass filters**. This is an implementation of Paul Kellet's refined algorithm, which approximates the ideal $1/f$ spectral characteristic with high precision.

3.  **Band-Limiting**:
    The broadband pink noise is passed through precise **Biquad filters** to limit the frequency bandwidth:

    - **High-Pass Filter (HPF)**: Cutoff at 10 Hz.
    - **Low-Pass Filter (LPF)**: Cutoff at 22.4 kHz.
      This ensures signal energy is contained within the audible spectrum and free from DC offset or ultrasonic interference.

4.  **Level Calibration**:
    The algorithm automatically scales the gain to align the output signal's RMS level precisely to the standard's target of **-18.5 dB AES FS** (approx. -21.5 dB FS).

---

## 🖥️ GUI Usage Guide

Built with Python's Tkinter library, this tool runs with minimal dependencies.

### How to Run

1.  Open your Terminal or Command Prompt.
2.  Execute the GUI script:
    ```bash
    python gui_generator.py
    ```

### Interface Features

1.  **Sample Rate**:
    - Select `48 kHz` (Broadcast standard) or `96 kHz` (High Res).
2.  **Duration**:
    - Enter the desired length of the audio in seconds.
3.  **Channel Count**:
    - Set the number of channels for the WAV file (e.g., 1 for Mono, 2 for Stereo). All channels will contain identical noise data.
4.  **Filename**:
    - Enter the name for the output file (the `.wav` extension is added automatically).
5.  **Output Folder**:
    - Click "Browse..." to select where the file should be saved.
6.  **Generate Audio**:
    - Click to start generation. The process runs in the background to keep the interface responsive.
7.  **Open Output Folder**:
    - Once generation is successful, this button becomes active. Click it to open the directory containing your new file.

### Verification

Upon completion, a popup will display the calculated **RMS (dB)** value, allowing you to verify that the signal meets the required reference level.
