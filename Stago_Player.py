import sys
import os
import wave
import struct
import hashlib
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QListWidget,
                             QFileDialog, QMessageBox, QInputDialog, QGroupBox,
                             QLineEdit, QTabWidget, QTextEdit, QProgressBar)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QIcon, QFont
import pygame


# --- Steganography Engine ---

class AudioStego:
    def __init__(self):
        pass

    def _xor_encrypt(self, data, password):
        """Simple XOR cipher to scramble data with password."""
        key = list(password)
        if not key: return data
        output = []
        for i, char in enumerate(data):
            output.append(chr(ord(char) ^ ord(key[i % len(key)])))
        return "".join(output)

    def embed_message(self, audio_path, output_path, message, password):
        """
        Hides message in the LSB of the audio file.
        Format: [HEADER_LEN_3_DIGITS][ENCRYPTED_MSG] + [DELIMITER]
        """
        try:
            song = wave.open(audio_path, mode='rb')
            # Read frames
            n_frames = song.getnframes()
            frames = song.readframes(n_frames)
            frame_bytes = bytearray(frames)

            # Prepare Payload
            # 1. Encrypt message
            encrypted_msg = self._xor_encrypt(message, password)
            # 2. Add Delimiter (to know when to stop reading)
            full_payload = encrypted_msg + "###END###"

            # Convert payload to binary bits
            bits = ''.join(format(ord(x), '08b') for x in full_payload)

            # Check Capacity
            if len(bits) > len(frame_bytes):
                song.close()
                return False, "Message too long for this audio file."

            # Embed Bits into LSB of audio bytes
            for i in range(len(bits)):
                # Clear LSB ( & 254) then Set LSB ( | bit)
                frame_bytes[i] = (frame_bytes[i] & 254) | int(bits[i])

            # Write modified frames to new file
            with wave.open(output_path, 'wb') as fd:
                fd.setparams(song.getparams())
                fd.writeframes(frame_bytes)

            song.close()
            return True, "Success"

        except Exception as e:
            return False, str(e)

    def extract_message(self, audio_path, password):
        """
        Extracts LSBs and attempts to reconstruct message.
        """
        try:
            song = wave.open(audio_path, mode='rb')
            n_frames = song.getnframes()
            frames = song.readframes(n_frames)
            frame_bytes = bytearray(frames)
            song.close()

            # Extract LSBs
            extracted_bits = [frame_bytes[i] & 1 for i in range(len(frame_bytes))]

            chars = []
            for i in range(0, len(extracted_bits), 8):
                byte = extracted_bits[i:i + 8]
                if len(byte) < 8: break

                # Convert 8 bits to char
                char_val = int("".join(map(str, byte)), 2)
                chars.append(chr(char_val))

                # Check for delimiter every character to save time
                # Optimization: In a huge file, we don't want to convert all bytes if msg is short
                if len(chars) > 9 and "".join(chars[-9:]) == "###END###":
                    break

            full_str = "".join(chars)

            if "###END###" in full_str:
                encrypted_content = full_str.split("###END###")[0]
                # Decrypt
                decrypted = self._xor_encrypt(encrypted_content, password)
                return True, decrypted
            else:
                return False, "No valid hidden message found (or wrong password format)."

        except Exception as e:
            return False, str(e)


# --- GUI Application ---

class MusicPlayerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GhostStream: Audio Player")
        self.setGeometry(100, 100, 600, 500)
        self.setStyleSheet("background-color: #222; color: #EEE;")

        self.stego = AudioStego()
        self.current_file = None

        # Init Audio Mixer
        pygame.mixer.init()

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # --- HEADER ---
        lbl_title = QLabel("GhostStream Player")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setFont(QFont("Arial", 18, QFont.Bold))
        lbl_title.setStyleSheet("color: #00AAFF; margin-bottom: 10px;")
        layout.addWidget(lbl_title)

        # --- PLAYLIST ---
        self.playlist = QListWidget()
        self.playlist.setStyleSheet("background-color: #333; border: 1px solid #555;")
        self.playlist.itemDoubleClicked.connect(self.load_selected_song)
        layout.addWidget(self.playlist)

        btn_add = QPushButton("Add .WAV File")
        btn_add.setStyleSheet("background-color: #444; padding: 5px;")
        btn_add.clicked.connect(self.add_file)
        layout.addWidget(btn_add)

        # --- PLAYBACK CONTROLS ---
        controls_layout = QHBoxLayout()

        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setStyleSheet("background-color: #00AA00; padding: 10px; font-weight: bold;")
        self.btn_play.clicked.connect(self.play_music)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setStyleSheet("background-color: #AA0000; padding: 10px; font-weight: bold;")
        self.btn_stop.clicked.connect(self.stop_music)

        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_stop)
        layout.addLayout(controls_layout)

        # --- SECRET OPERATIONS AREA ---
        # Look like a standard equalizer or settings area until clicked
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; } 
            QTabBar::tab { background: #333; color: #AAA; padding: 8px; } 
            QTabBar::tab:selected { background: #555; color: #FFF; }
        """)
        self.tabs.setMaximumHeight(200)

        # Tab 1: Encode
        tab_enc = QWidget()
        vbox_enc = QVBoxLayout(tab_enc)

        self.input_secret = QLineEdit()
        self.input_secret.setPlaceholderText("Enter secret message to hide...")

        self.input_pass_enc = QLineEdit()
        self.input_pass_enc.setPlaceholderText("Password Lock")
        self.input_pass_enc.setEchoMode(QLineEdit.Password)

        btn_encode = QPushButton("Inject Data into Song")
        btn_encode.setStyleSheet("background-color: #555; border: 1px solid #777;")
        btn_encode.clicked.connect(self.run_encode)

        vbox_enc.addWidget(self.input_secret)
        vbox_enc.addWidget(self.input_pass_enc)
        vbox_enc.addWidget(btn_encode)

        # Tab 2: Decode
        tab_dec = QWidget()
        vbox_dec = QVBoxLayout(tab_dec)

        self.input_pass_dec = QLineEdit()
        self.input_pass_dec.setPlaceholderText("Enter Password to Unlock")
        self.input_pass_dec.setEchoMode(QLineEdit.Password)

        btn_decode = QPushButton("Extract Hidden Message")
        btn_decode.setStyleSheet("background-color: #555; border: 1px solid #777;")
        btn_decode.clicked.connect(self.run_decode)

        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setPlaceholderText("Decoded text will appear here...")

        vbox_dec.addWidget(self.input_pass_dec)
        vbox_dec.addWidget(btn_decode)
        vbox_dec.addWidget(self.txt_result)

        self.tabs.addTab(tab_enc, "Encoder (Inject)")
        self.tabs.addTab(tab_dec, "Decoder (Extract)")

        layout.addWidget(self.tabs)

    # --- GUI LOGIC ---

    def add_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open Audio', '', 'WAV Files (*.wav)')
        if fname:
            self.playlist.addItem(fname)

    def load_selected_song(self, item):
        self.current_file = item.text()
        QMessageBox.information(self, "Loaded", f"Selected: {os.path.basename(self.current_file)}")

    def play_music(self):
        if self.playlist.currentItem():
            fpath = self.playlist.currentItem().text()
            try:
                pygame.mixer.music.load(fpath)
                pygame.mixer.music.play()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not play file: {e}")
        else:
            QMessageBox.warning(self, "Warning", "Select a song from the playlist first.")

    def stop_music(self):
        pygame.mixer.music.stop()

    def run_encode(self):
        if not self.playlist.currentItem():
            QMessageBox.warning(self, "Error", "Select a base song from playlist.")
            return

        src_path = self.playlist.currentItem().text()
        msg = self.input_secret.text()
        pwd = self.input_pass_enc.text()

        if not msg or not pwd:
            QMessageBox.warning(self, "Error", "Message and Password required.")
            return

        # Ask where to save
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Stego Song", "", "WAV Files (*.wav)")
        if not save_path: return

        success, info = self.stego.embed_message(src_path, save_path, msg, pwd)

        if success:
            QMessageBox.information(self, "Success",
                                    "Data injected successfully!\nThe new file works like a normal song.")
            self.playlist.addItem(save_path)  # Add new ghost song to playlist
            self.input_secret.clear()
            self.input_pass_enc.clear()
        else:
            QMessageBox.critical(self, "Encoding Failed", info)

    def run_decode(self):
        if not self.playlist.currentItem():
            QMessageBox.warning(self, "Error", "Select a song to analyze.")
            return

        src_path = self.playlist.currentItem().text()
        pwd = self.input_pass_dec.text()

        if not pwd:
            QMessageBox.warning(self, "Error", "Password required to unlock.")
            return

        success, result = self.stego.extract_message(src_path, pwd)

        if success:
            self.txt_result.setText(result)
        else:
            self.txt_result.setText(f"[ERROR]: {result}\n(Did you use the correct password?)")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MusicPlayerGUI()
    window.show()
    sys.exit(app.exec_())