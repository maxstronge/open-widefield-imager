from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLabel, QLineEdit, QSpinBox, QHBoxLayout, QSlider, QDoubleSpinBox,QSplitter, QGroupBox
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, QTime
from PyQt5.QtGui import QImage, QPixmap
import cv2
import threading
import time
import serial
import serial.tools.list_ports
from qt_material import apply_stylesheet
import mvsdk
import numpy as np
import yaml
import os
import queue
os.add_dll_directory("C:\Windows\System32")


from PyQt5.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QVBoxLayout, QWidget
from PyQt5.QtCore import QTime

class TimePicker(QWidget):
    """Custom widget for entering capture duration in days:hours:minutes:seconds."""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("dd:hh:mm:ss")
        self.time_input.setInputMask("00:00:00:00")  # Mask for days:hours:minutes:seconds
        self.time_input.installEventFilter(self)  # Filter input events to handle mouse click
        self.time_input.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_input)

        self.setLayout(layout)

    def get_duration_in_seconds(self):
        """Parse the time input and return total duration in seconds."""
        text = self.time_input.text()
        try:
            days, hours, minutes, seconds = map(int, text.split(":"))
            return days * 86400 + hours * 3600 + minutes * 60 + seconds
        except ValueError:
            return 0
        
    def eventFilter(self, source, event):
        """
        Handle a mouse click to properly set cursor position in the QLineEdit.
        """
        if source==self.time_input and event.type()==event.MouseButtonPress:
            self.time_input.setFocus()
            self.time_input.setCursorPosition(0)
            return True
        return super().eventFilter(source, event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = {}
        self.load_config()
        self.init_ui()
        self.arduino = None  # initializing as none as I don't have an arduino with me atm
        self.hCamera = None
        self.frame_queue = queue.Queue()
        self.display_thread = None
        self.camera_running = False

        self.initialize_camera()
        self.initialize_arduino()

# CONFIGURATION (saves to/loads from the config.yml file so settings can be saved between sessions)


    def load_config(self):
        """Load settings from config.yml into self.config."""
        try:
            with open("config.yml", "r") as f:
                self.config = yaml.safe_load(f) or {}
            print("Configuration loaded.")
        except FileNotFoundError:
            print("Config file not found, using defaults.")
            self.config = {}

        # Ensure default structure
        self.config.setdefault("CAMERA", {
            "EXPOSURE_TIME": 1.0,
            "ANALOG_GAIN": 10,
            "SAVE_DIR": "C://OWFI/",
            "CAPTURE_DURATION": 0 # 0 means perpetual capture
        })

        self.config.setdefault("ARDUINO", {
            "PORT": "COM3",
            "F_LED": 25,
            "E_LED": 18,
            "T_CAM": 1,
            "O_CAM": 2,
            "EXTERN": 0,
        })


    def save_config(self):
        """Save current settings to config.yml."""
        # Camera config
        self.config["CAMERA"] = {
            "EXPOSURE_TIME": self.camera_exposure_input.value(),
            "ANALOG_GAIN": self.camera_gain_slider.value(),
            "SAVE_DIR": self.config["CAMERA"].get("SAVE_DIR", "C://OWFI/"),  # Keep existing save directory
            "CAPTURE_DURATION": self.capture_duration_input.value(),
        }
        # Arduino config
        self.config["ARDUINO"] = {
            "PORT": self.arduino_port_input.text(),
            "F_LED": self.f_led_input.value(),
            "E_LED": self.e_led_input.value(),
            "T_CAM": self.t_cam_input.value(),
            "O_CAM": self.o_cam_input.value(),
            "EXTERN": self.extern_input.value(),
        }

        with open("config.yml", "w") as f:
            yaml.dump(self.config, f)
        print("Configuration saved.")

# GUI
    def init_ui(self):
        """
        Initialize the user interface layout and widgets.
        """
        self.setWindowTitle("Open Wide-Field Imaging GUI")
        self.setGeometry(100, 100, 1200, 700)

        apply_stylesheet(app, theme="dark_blue.xml")

        # Live Preview
        self.video_label = QLabel("Live Preview")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white; font-size: 20px;")
        self.video_label.setFixedSize(800, 600)

        # Common stylesheet for parameter labels
        param_label_style = "font-size: 12px; font-weight: normal; color: #cfcfcf;"

        # Camera Settings Group
        camera_group = QGroupBox("Camera Settings")
        camera_group.setStyleSheet("font-size: 16px; font-weight: bold;")
        camera_layout = QVBoxLayout()

        self.camera_exposure_input = QDoubleSpinBox()
        self.camera_exposure_input.setDecimals(2)
        self.camera_exposure_input.setRange(0.01, 100.0)
        self.camera_exposure_input.setValue(self.config["CAMERA"].get("EXPOSURE_TIME", 1.0))
        self.camera_exposure_input.setStyleSheet("color: white;")
        camera_label = QLabel("Exposure Time (ms):")
        camera_label.setStyleSheet(param_label_style)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_exposure_input)

        self.camera_gain_slider = QSlider(Qt.Horizontal)
        self.camera_gain_slider.setMinimum(1)
        self.camera_gain_slider.setMaximum(100)
        self.camera_gain_slider.setValue(self.config["CAMERA"].get("ANALOG_GAIN", 10))
        self.camera_gain_slider.setStyleSheet("color: white;")
        self.camera_gain_label = QLabel(f"Analog Gain: {self.camera_gain_slider.value()}")
        self.camera_gain_label.setStyleSheet(param_label_style)
        camera_layout.addWidget(self.camera_gain_label)
        camera_layout.addWidget(self.camera_gain_slider)
        self.camera_gain_slider.valueChanged.connect(
            lambda value: self.camera_gain_label.setText(f"Analog Gain: {value}")
        )

        camera_group.setLayout(camera_layout)

        # Time Input Widget
        duration_label = QLabel("Capture Duration (hh:mm:ss):")
        duration_label.setAlignment(Qt.AlignCenter)
        duration_label.setStyleSheet("font-size: 14px; color: white;")

        time_input_layout = QHBoxLayout()

        self.hours_input = QSpinBox()
        self.hours_input.setRange(0, 23)  # Max 23 hours
        self.hours_input.setSuffix(" h")
        self.hours_input.setStyleSheet("color: white;")
        time_input_layout.addWidget(self.hours_input)

        self.minutes_input = QSpinBox()
        self.minutes_input.setRange(0, 59)  # Max 59 minutes
        self.minutes_input.setSuffix(" m")
        self.minutes_input.setStyleSheet("color: white;")
        time_input_layout.addWidget(self.minutes_input)

        self.seconds_input = QSpinBox()
        self.seconds_input.setRange(0, 59)  # Max 59 seconds
        self.seconds_input.setSuffix(" s")
        self.seconds_input.setStyleSheet("color: white;")
        time_input_layout.addWidget(self.seconds_input)

        time_input_widget = QWidget()
        time_input_widget.setLayout(time_input_layout)



        # Arduino Settings Group
        arduino_group = QGroupBox("Arduino Settings")
        arduino_group.setStyleSheet("font-size: 16px; font-weight: bold;")
        arduino_layout = QVBoxLayout()

        self.arduino_port_input = QLineEdit()
        self.arduino_port_input.setPlaceholderText("Enter Arduino Port (e.g., COM3)")
        self.arduino_port_input.setText(self.config["ARDUINO"].get("PORT", "COM3"))
        self.arduino_port_input.setStyleSheet("color: white;")
        arduino_label = QLabel("Arduino Port:")
        arduino_label.setStyleSheet(param_label_style)
        arduino_layout.addWidget(arduino_label)
        arduino_layout.addWidget(self.arduino_port_input)

        self.f_led_input = QSpinBox()
        self.f_led_input.setRange(1, 1000)
        self.f_led_input.setValue(self.config["ARDUINO"].get("F_LED", 25))
        self.f_led_input.setStyleSheet("color: white;")
        f_led_label = QLabel("LED Frequency (F_LED, Hz):")
        f_led_label.setStyleSheet(param_label_style)
        arduino_layout.addWidget(f_led_label)
        arduino_layout.addWidget(self.f_led_input)

        self.e_led_input = QSpinBox()
        self.e_led_input.setRange(1, 100)
        self.e_led_input.setValue(self.config["ARDUINO"].get("E_LED", 18))
        self.e_led_input.setStyleSheet("color: white;")
        e_led_label = QLabel("LED Exposure Time (E_LED, ms):")
        e_led_label.setStyleSheet(param_label_style)
        arduino_layout.addWidget(e_led_label)
        arduino_layout.addWidget(self.e_led_input)

        self.t_cam_input = QSpinBox()
        self.t_cam_input.setRange(1, 100)
        self.t_cam_input.setValue(self.config["ARDUINO"].get("T_CAM", 1))
        self.t_cam_input.setStyleSheet("color: white;")
        t_cam_label = QLabel("Camera Signal Duration (T_CAM, ms):")
        t_cam_label.setStyleSheet(param_label_style)
        arduino_layout.addWidget(t_cam_label)
        arduino_layout.addWidget(self.t_cam_input)

        self.o_cam_input = QSpinBox()
        self.o_cam_input.setRange(0, 100)
        self.o_cam_input.setValue(self.config["ARDUINO"].get("O_CAM", 2))
        self.o_cam_input.setStyleSheet("color: white;")
        o_cam_label = QLabel("Camera Offset Time (O_CAM, ms):")
        o_cam_label.setStyleSheet(param_label_style)
        arduino_layout.addWidget(o_cam_label)
        arduino_layout.addWidget(self.o_cam_input)

        self.extern_input = QSpinBox()
        self.extern_input.setRange(0, 1)
        self.extern_input.setValue(self.config["ARDUINO"].get("EXTERN", 0))
        self.extern_input.setStyleSheet("color: white;")
        extern_label = QLabel("External Exposure (EXTERN, 0 or 1):")
        extern_label.setStyleSheet(param_label_style)
        arduino_layout.addWidget(extern_label)
        arduino_layout.addWidget(self.extern_input)

        arduino_group.setLayout(arduino_layout)


        # Buttons
        self.start_button = QPushButton("Start Capture")
        self.stop_button = QPushButton("Stop Capture")
        self.set_params_button = QPushButton("Set Parameters")
        self.retry_button = QPushButton("Retry Arduino Connection")

        self.start_button.clicked.connect(self.start_capture)
        self.stop_button.clicked.connect(self.stop_capture)
        self.set_params_button.clicked.connect(self.set_parameters)
        self.retry_button.clicked.connect(self.retry_arduino_connection)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.set_params_button)
        button_layout.addWidget(self.retry_button)

        button_widget = QWidget()
        button_widget.setLayout(button_layout)

        # Main Layout
        main_layout = QVBoxLayout()

        # Splitter for main view
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.video_label)  # Live preview
        settings_widget = QWidget()
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(camera_group)
        settings_layout.addWidget(arduino_group)
        settings_widget.setLayout(settings_layout)
        splitter.addWidget(settings_widget)
        splitter.setStretchFactor(0, 3)  # Live preview larger
        splitter.setStretchFactor(1, 1)  # Settings smaller

        main_layout.addWidget(splitter)

        # Time Picker for Capture Duration
        duration_label = QLabel("Capture Duration (dd:hh:mm:ss):")
        duration_label.setAlignment(Qt.AlignCenter)
        duration_label.setStyleSheet("font-size: 14px; color: white;")

        self.time_picker = TimePicker()

        main_layout.addWidget(duration_label)
        main_layout.addWidget(self.time_picker)
        main_layout.addWidget(button_widget)  # Buttons below the time picker


        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)


# INITIALIZATION

    def initialize_camera(self):
        try:
            # list available cameras
            DevList = mvsdk.CameraEnumerateDevice()
            if len(DevList) < 1:
                print("No camera found!")
                self.video_label.setText("No camera found!")
                return

            # select the first available camera
            DevInfo = DevList[0]  
            self.hCamera = mvsdk.CameraInit(DevInfo, -1, -1)

            # Get camera capabilities
            cap = mvsdk.CameraGetCapability(self.hCamera)
            print(f"Expected buffer size: {cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax}") 
            self.height = cap.sResolutionRange.iHeightMax
            self.width = cap.sResolutionRange.iWidthMax
            print(f"Camera resolution: {self.width}x{self.height}")

            # Configure the camera
            mvsdk.CameraSetTriggerMode(self.hCamera, 0) # continuous mode at launch for live preview
            mvsdk.CameraSetFrameSpeed(self.hCamera, 1)  # High-speed mode
            mvsdk.CameraSetAeState(self.hCamera, 0)  # Manual exposure
            mvsdk.CameraSetExposureTime(self.hCamera, self.camera_exposure_input.value() * 1000)  # Initial exposure
            mvsdk.CameraSetAnalogGain(self.hCamera, self.camera_gain_slider.value())  # Initial gain
            mvsdk.CameraPlay(self.hCamera)  # Start the camera

            # allocate frame buffer
            FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax
            self.pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

            # start live feed thread
            self.camera_running = True
            self.display_thread = threading.Thread(target=self.display_frames, daemon=True)
            self.display_thread.start()

            print("Camera initialized successfully.")

        except Exception as e:
            print(f"Failed to initialize the camera: {e}")
            self.video_label.setText("Failed to initialize the camera. Check console for details.")

    def initialize_arduino(self):
        try:
            port = self.config.get("ARDUINO_PORT","COM9")  # Default port
            # Attempt to connect to the Arduino
            self.arduino = serial.Serial(port, 9600, timeout=1)  
            print("Arduino connected successfully.")
        except serial.SerialException as e:
            print(f"Could not connect to Arduino: {e}")
            print("You can connect it later and retry using the 'Retry Arduino' button.")
    
    def closeEvent(self, event):
        """
        Handle the window close event gracefully if possible
        """
        self.save_config()  # Save current settings
        self.camera_running = False
        if self.display_thread:
            self.display_thread.join()
        if self.hCamera:
            mvsdk.CameraUnInit(self.hCamera)
        if hasattr(self, "pFrameBuffer"):
            mvsdk.CameraAlignFree(self.pFrameBuffer)
        if self.arduino:
            self.arduino.close()
        event.accept()

    # there is very probably a less lame way to do this
    def retry_arduino_connection(self):
        self.initialize_arduino()

# ARDUINO COMMUNICATION

    def send_arduino_command(self, command):
        if not self.arduino:
            print("Arduino not connected.")
            return False
        self.arduino.write(command.encode('utf-8'))
        time.sleep(0.1)  # Give the Arduino time to process
        if self.arduino.in_waiting:
            response = self.arduino.readline().decode('utf-8').strip()
            print(f"Arduino response: {response}")
            return response
        return False

    def set_parameters(self):
        """Send parameters to the Arduino."""
        if not self.arduino:
            print("Arduino not connected.")
            return

        # Construct the parameter string
        params = f"S {self.f_led_input.value()} {self.e_led_input.value()} {self.t_cam_input.value()} {self.o_cam_input.value()} {self.extern_input.value()}\n"
        response = self.send_arduino_command(params)
        print(f"Sent parameters: {params.strip()}")
        if response:
            print(f"Arduino response: {response}")

    def start_capture(self):
        """Start the capture process, including initializing Arduino, setting parameters, and starting the signal generator."""
        if not self.arduino:
            print("Arduino not connected.")
            return

        
        self.camera_running = False  # Stop the live preview

        if self.display_thread:
            self.display_thread.join()  # Wait for the display thread to stop


        # Start capturing
        print("Triggering capture...")
        self.switch_trigger_mode(2)  # Switch to hardware trigger mode
        self.send_arduino_command(b'X\n')  # Command Arduino to begin capture
        print("Capture started. Hardware trigger mode enabled.")

        # Set up capture duration
        capture_duration = self.time_picker.get_duration_in_seconds()
        if capture_duration > 0:
            self.video_label.setStyleSheet("background-color: black; color: white; font-size: 24px;")
            threading.Timer(capture_duration, self.stop_capture).start()
            print(f"Capture will stop automatically after {capture_duration} seconds.")


    def stop_capture(self):
        """Stop the capture process by sending the appropriate command to the Arduino."""
        if not self.arduino:
            print("Arduino not connected.")
            return
        
        try:
            print("Stopping capture...")
            self.send_arduino_command(b'Q\n')  # Command Arduino to stop capturing
            self.switch_trigger_mode(0)  # Switch back to continuous mode


            # Reset the live preview
            if not self.display_thread or not self.display_thread.is_alive(): # making sure only one threat is running at a time
                self.camera_running = True
                self.display_thread = threading.Thread(target=self.display_frames, daemon=True)
                self.display_thread.start()
            
        
        except Exception as e:
            print(f"Failed to stop capture: {e}")



# CAMERA CONTROL

    # Callback function for camera frames
    @mvsdk.method(mvsdk.CAMERA_SNAP_PROC)
    def GrabCallback(self, hCamera, pRawData, pFrameHead, pContext):
        # print("GrabCallback") 
        try:
            # Convert the buffer to a NumPy array
            # print("Callback triggered")
            frame_data = (mvsdk.c_ubyte * pFrameHead.contents.uBytes).from_address(pRawData)
            self.frame_queue.put(frame_data)
        finally:
            mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)


    def switch_trigger_mode(self, mode):
        """Switch the camera's trigger mode.
        
        0: Continuous mode, suitable for live view

        
        2: Hardware trigger mode, capturing frames when trigger is recieved from the arduino
        """
        # Map mode numbers to human-readable strings
        mode_map = {
            0: "continuous recording",
            2: "hardware trigger"
        }
        try:
            mvsdk.CameraSetTriggerMode(self.hCamera, mode)
            print(f"Trigger mode set to {mode_map[mode]}.")
        except Exception as e:
            print(f"Failed to set trigger mode: {e}")

    def display_frames(self):
        print("Display frames thread started.")
        while self.camera_running:
            try:
                # Capture a frame
                FrameHead, pFrameBuffer, FrameData = mvsdk.CameraGetImageBuffer(self.hCamera, 200)
                frame = np.frombuffer(FrameData, dtype=np.uint8).reshape((FrameHead.iHeight, FrameHead.iWidth))

                # Convert to QImage for display
                h, w = frame.shape
                bytes_per_line = w  # Grayscale has one byte per pixel
                q_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_Grayscale8)

                # Update QLabel
                pixmap = QPixmap.fromImage(q_image)
                self.video_label.setPixmap(pixmap)

                # Release the buffer
                mvsdk.CameraReleaseImageBuffer(self.hCamera, FrameHead)
            except mvsdk.CameraException as e:
                print(f"Error capturing frame: {e}")
                break

        print("Live preview stopped.")

    def save_frames(self):
        """Capture and save the current frame."""
        try:
            FrameHead, pFrameBuffer, FrameData = mvsdk.CameraGetImageBuffer(self.hCamera, 200)
            frame = np.frombuffer(FrameData, dtype=np.uint8).reshape((self.height, self.width))
            
            # Use the save directory from the config
            save_dir = self.config["CAMERA"].get("SAVE_DIR", "C://OWFI/")
            filename = os.path.join(save_dir, f"capture_{int(time.time())}.jpg")
            
            os.makedirs(save_dir, exist_ok=True)  # Ensure directory exists
            cv2.imwrite(filename, frame)
            print(f"Frame saved as {filename}")

            mvsdk.CameraReleaseImageBuffer(self.hCamera, FrameHead)
        except Exception as e:
            print(f"Failed to save frame: {e}")


    def adjust_exposure(self, value):
        """Adjust the camera's exposure."""
        try:
            mvsdk.CameraSetExposureTime(self.hCamera, value * 1000)
            print(f"Exposure adjusted to {value} ms")
        except Exception as e:
            print(f"Failed to adjust exposure: {e}")

    def adjust_gain(self, value):
        """Adjust the camera's gain."""
        try:
            mvsdk.CameraSetAnalogGain(self.hCamera, value)
            print(f"Gain adjusted to {value}")
        except Exception as e:
            print(f"Failed to adjust gain: {e}")


# Run the application
app = QApplication([])



window = MainWindow()
window.show()
app.exec()