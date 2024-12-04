# Open WideField Imager

GUI to control a widefield imaging setup, integrating Arduino controls and camera preview/capture into a unified experience. PHYS599 undergraduate research thesis. 

![image](https://github.com/user-attachments/assets/973a24ce-9089-4072-add0-46de368b6ae0)


Currently supports Windows only.

## Setup:

Clone the repo to your local machine or download the .zip to a directory of your choice. 

Add the included MKCAMSDK.dll to the System32 folder of the computer.

Ensure the widefield_ctrl.ino arduino code is loaded onto the arduino.

Connect both the arduino and the camera to the computer. Note the COM port the Arduino is connected to - you'll need to provide this to the program later. 

Open up the configuration file (config.yml) and set the value of SAVE_DIR to the full path of the directory you'd like to save output to. 

Launch gui.py. The arduino and camera should automatically connect and a live feed will be previewed in the window.

## Usage:

If the arduino does not automatically connect, change the COM port in the settings tab on the right side and click 'Retry Arduino Connection'. Check the console output to verify that it connects properly. 

The settings tab on the right includes controls to modify the exposure time and gain of the camera, as well as the inputs the arduino code is expecting. The defaults for the arduino code should be fine. Whenever these settings are changed, they are saved to the config.yml file so they'll be loaded again when the program next starts up. 

When you're ready to begin capturing, click Set Parameters to send the input parameters to the Arduino. You should see a confirmation in the console output, and the excitation LEDs will begin flashing. 

Set a capture duration for the experiment in the time input field (dd:hh:mm:ss). If this is not set, the program will capture indefinitely until the Stop Capture button is pressed. 

Press the Start Capture button to begin capturing frames when the Arduino sends the trigger to the camera. Frames with metadata will be saved to the output directory. 

## To Do:

- Make the time picker UX more friendly
- Display a countdown on the screen when a timed recording is in progress


Please feel free to make pull requests with any suggested improvements! 
