#include <math.h>

// 2 3 4 5 - D2 D3 D4 D5
const int violetPin = 2; // the number of the 405 laser pin 2
const int bluePin = 3; // the number of the 465 laser pin 3
const int cameraPin = 4; // the number of the camera pin 4
const int cameraInputPin = 5; // the number of the camera pin 5

int violetState = LOW; // violetState used to set the laser
int blueState = LOW; // blueState used to set the laser
int cameraState = LOW; // cameraState used to set the camera output
int cameraInput = LOW; // cameraInput used to set the camera input

// All these units in ms - Default values
float cameraUpDurationDef = 1; // 1 ms
float cameraUpOffsetDef = 2; // 2 ms
float LEDperiodDef = 40;
float exposureDurationDef = 15; // Has to be smaller than led period

// Variable conversion
float cameraUpDuration = cameraUpDurationDef;
float LEDperiod = LEDperiodDef;
float exposureDuration = exposureDurationDef;
float cameraUpOffset = cameraUpOffsetDef;
unsigned long t;

boolean newData = false;
float dataNumber = 0;
const byte numChars = 32;
char receivedChars[numChars];   // an array to store the received data
boolean periodSet = false;
boolean exposureSet = false;
boolean externalAcquire = false;
bool waveRunning = false;

unsigned long timer = 0;
int timerMultiplier = 0;

String receivedText, tmpStr;
void setup()
{
  pinMode(violetPin, OUTPUT);
  pinMode(bluePin, OUTPUT);
  pinMode(cameraPin, OUTPUT);
  pinMode(cameraInputPin, INPUT);
  Serial.begin(9600);
  while (!Serial); // Wait untilSerial is ready
  printHelpMsg();

  //TCCR0A=(1<<WGM01);    //Set the CTC mode
  TCCR2B = (1 << WGM01); //Set the CTC mode
  //OCR0A=0xF9; //Value for ORC0A for 1ms
  //OCR2A = 0xF9; //Value for ORC0A for 1ms
  OCR2A = 0x64; // To have 0.05 ms resolution with 010 prescaler

  //TIMSK0|=(1<<OCIE0A);   //Set the interrupt request
  TIMSK2 = (1 << OCIE2A); //Set the interrupt request
  sei(); //Enable interrupt

  TCCR2B = (0 << CS22) + (1 << CS21) + (0 << CS20); // 100 for ms - 011 for a 2X - 010 for 8X
  //timerMultiplier = 20; // For 1 ms scale with 0x64 and 010 (20x the 0.05 ms ticks)
  timerMultiplier = 8; // New test?
  //timerMultiplier = 8; // 1 for ms in 100
  //TCCR2B= (1 << CS22) + (0 << CS21) + (0 << CS20); // 100 for ms - 011 for a 2X - 010 for 8X
  //TCCR0B|= (1 << CS01);    // For 32 / factor of 4
  //TCCR0B|=(1<<CS01);    //Set the prescale 1/64 clock
  //TCCR0B|=(1<<CS00);

}

void loop()
{
  // Check for a new line
  recvWithEndMarker();
  if (newData == true)
  {
    // Get the line and reset
    receivedText = String(receivedChars);
    receivedText.toUpperCase();
    //dataNumber = atof(receivedChars);   // new for this version
    newData = false;

    if (receivedText.equals("H"))
    {
      printHelpMsg();
      return;
    }
    else if (receivedText.startsWith("S"))
    {
      if (waveRunning)
      {
        Serial.println("Stopping current signal before updating parameters ...");
        waveRunning = false;
        externalAcquire = false;
        violetState = LOW;
        blueState = LOW;
        cameraState = LOW;
        digitalWrite(violetPin, violetState);
        digitalWrite(bluePin, blueState);
        digitalWrite(cameraPin, cameraState);
      }
      //String getValue(String data, char separator, int index)
      //Serial.println("'S F_LED E_LED T_CAM O_CAM EXTERN' - To set the paramters:");
      Serial.println(F("Updating parameters:"));

      tmpStr = getValue(receivedText, ' ', 1); // F_LED
      if (tmpStr.toFloat() > 0)
      {
        LEDperiod = 1000 / tmpStr.toFloat();
        Serial.println("LED freq: " + String(1000 / LEDperiod, 2) + " Hz - Period: " + String(LEDperiod, 2) + " ms.");
      }
      else
      {
        LEDperiod = LEDperiodDef;
        Serial.println("Invalid LED freq. Using default: " + String(1000 / LEDperiod, 2) + " Hz.");
      }

      tmpStr = getValue(receivedText, ' ', 2); // E_LED
      if (tmpStr.toFloat() > 0)
      {
        exposureDuration = tmpStr.toFloat();
        Serial.println("LED exposure: " + String(exposureDuration, 2) + " ms.");
      }
      else
      {
        exposureDuration = exposureDurationDef;
        Serial.println("Invalid LED exposure. Using default: " + String(exposureDuration, 2) + " ms.");
      }

      tmpStr = getValue(receivedText, ' ', 3); // T_CAM
      if (tmpStr.toFloat() > 0)
      {
        cameraUpDuration = tmpStr.toFloat();
        Serial.println("Camera acquisition UP duration: " + String(cameraUpDuration, 2) + " ms.");
      }
      else
      {
        cameraUpDuration = cameraUpDurationDef;
        Serial.println("Invalid Camera acquisition UP duration. Using default: " + String(cameraUpDuration, 2) + " ms.");
      }

      tmpStr = getValue(receivedText, ' ', 4); // O_CAM
      if (tmpStr.toFloat() > 0)
      {
        cameraUpOffset = tmpStr.toFloat();
        Serial.println("Camera acquisition offset: " + String(cameraUpOffset, 2) + " ms.");
      }
      else
      {
        cameraUpOffset = cameraUpOffsetDef;
        Serial.println("Invalid Camera acquisition offset. Using default: " + String(cameraUpOffset, 2) + " ms.");
      }

      tmpStr = getValue(receivedText, ' ', 5); // EXTERN
      if (tmpStr.toInt() > 0)
      {
        externalAcquire = true;
        Serial.println("External acquire set to true");
      }
      else
      {
        externalAcquire = false;
        Serial.println("External acquire set to false");
      }
    }
    else if (receivedText.equals("X"))
    {
      waveRunning = true;
      violetState = LOW;
      blueState = LOW;
      cameraState = LOW;
      digitalWrite(violetPin, violetState);
      digitalWrite(bluePin, blueState);
      digitalWrite(cameraPin, cameraState);
      // Do some initialization
      Serial.println(F("Starting the signal..."));
      timer = 0;
    }
    else if (receivedText.equals("Q"))
    {
      waveRunning = false;
      violetState = LOW;
      blueState = LOW;
      cameraState = LOW;
      Serial.println(F("Stopping the signal..."));
      digitalWrite(violetPin, violetState);
      digitalWrite(bluePin, blueState);
      digitalWrite(cameraPin, cameraState);
    }
    //Serial.println("'S F_LED E_LED T_CAM O_CAM' - To set the paramters:");
  }

  // Generate the actual signal
  if (waveRunning)
  {
    if (externalAcquire)
    {
      cameraInput = digitalRead(cameraInputPin); 
    }
    // Timer reset
    if (timer >= 2 * LEDperiod * timerMultiplier)
    {
      timer = 0;
    }
    t = timer;
    // LED 1 start
    //if (fmod(t, 2 * LEDperiod * timerMultiplier) >= 0 && fmod(t, 2 * LEDperiod * timerMultiplier) < exposureDuration * timerMultiplier)
    if ((t % long(2 * LEDperiod * timerMultiplier)) >= 0 && (t % long(2 * LEDperiod * timerMultiplier)) < exposureDuration * timerMultiplier)
    {
      // We are on the first half of the period
      violetState = LOW;
      blueState = HIGH;
      //   Serial.println("1");
    }
    // LED 2 start
    //else if (fmod(t, 2 * LEDperiod * timerMultiplier) >= 0 && fmod(t, 2 * LEDperiod * timerMultiplier) >= LEDperiod * timerMultiplier && fmod(t,  2 * LEDperiod * timerMultiplier) <= (LEDperiod + exposureDuration)*timerMultiplier)
    else if ((t % long(2 * LEDperiod * timerMultiplier)) >= 0 && (t % long(2 * LEDperiod * timerMultiplier)) >= LEDperiod * timerMultiplier && (t %  long(2 * LEDperiod * timerMultiplier)) <= (LEDperiod + exposureDuration)*timerMultiplier)
    {
      // We are on the second half
      violetState = HIGH;
      blueState = LOW;
    }
    else
    {
      // Just in case
      violetState = LOW;
      blueState = LOW;
    }
    // Camera exposure start
    //if (fmod(t, (LEDperiod * timerMultiplier)) >= cameraUpOffset * timerMultiplier && fmod(t, LEDperiod * timerMultiplier) < (cameraUpDuration + cameraUpOffset)*timerMultiplier)
    // Signal is on after a time cameraUpOffset after a LED rise for cameraUpDuration time IF external acquire is OFF or the external signal is HIGH
    if ((!externalAcquire || cameraInput == HIGH) &&
      (t % long(LEDperiod * timerMultiplier)) >= cameraUpOffset * timerMultiplier && 
      (t % long(LEDperiod * timerMultiplier)) < (cameraUpDuration + cameraUpOffset)*timerMultiplier)
      //if ((t % (cameraPeriod)) >= 0 && (t % cameraPeriod) < (ulCameraUpDuration))
    {
      // Now the camera
      cameraState = HIGH;
    }
    else
    {
      cameraState = LOW;
    }
    //Serial.println(violetState);
    digitalWrite(violetPin, violetState);
    digitalWrite(bluePin, blueState);
    digitalWrite(cameraPin, cameraState);
  }
}

void printHelpMsg() {
  Serial.println(F("Dual wavelength signal generator"));
  Serial.println(F("-----------------------------------"));
  Serial.println(F("Available commands:"));
  Serial.println(F(""));
  Serial.println(F("'S F_LED E_LED T_CAM O_CAM EXTERN' - To set the paramters:"));
  Serial.println(F("   F_LED: freq (Hz) of LED switching (corresponds to the camera fps)"));
  Serial.println(F("   E_LED: exposure time (ms) of each LED  (time each LED is ON has to be lower than 1/F_LED)"));
  Serial.println(F("   T_CAM: duration (ms) of camera acquisition signal (1 ms is usally fine. The actual exposure is controlled by the camera options)"));
  Serial.println(F("   O_CAM: offset time (s) between LED is on and camera frame acquisition starts (2ms is usually fine)"));
  Serial.println(F("   EXTERN: whether the overall camera exposure is controlled by an external signal (0 or 1 for false/true)"));
  Serial.println(F("   Example: S 25 18 1 2 0"));
  Serial.println(F("   Notes:"));
  Serial.println(F("   The timing resolution is 0.05 ms (every parameter will be rounded to the closest 0.05 ms interval)."));
  Serial.println(F("   In this example, the LED freq is 25 Hz, so the camera will capture at 25 Hz (interleaved frames), and each LED will have a 12.5 Hz freq."));
  Serial.println(F("   The LED exposure is the time the LED is ON. It is NOT the camera exposure, that one is set externally (usually lower than the LED exposure)."));
  Serial.println(F("'X' - To start the signal generator"));
  Serial.println(F("'Q' - To stop the signal generator"));
  Serial.println(F("'H' - To display this message"));
  Serial.println(F(""));
}

void recvWithEndMarker() {
  static byte ndx = 0;
  char endMarker = '\n';
  char rc;
  if (Serial.available() > 0) {
    rc = Serial.read();

    if (rc != endMarker) {
      receivedChars[ndx] = rc;
      ndx++;
      if (ndx >= numChars) {
        ndx = numChars - 1;
      }
    }
    else {
      receivedChars[ndx] = '\0'; // terminate the string
      ndx = 0;
      newData = true;
    }
  }
}

// TO split the strings
String getValue(String data, char separator, int index)
{
  int maxIndex = data.length() - 1;
  int j = 0;
  String chunkVal = "";

  for (int i = 0; i <= maxIndex && j <= index; i++)
  {
    chunkVal.concat(data[i]);

    if (data[i] == separator)
    {
      j++;

      if (j > index)
      {
        chunkVal.trim();
        return chunkVal;
      }

      chunkVal = "";
    }
    else if ((i == maxIndex) && (j < index)) {
      chunkVal = "";
      return chunkVal;
    }
  }
}

//ISR(TIMER0_COMPA_vect){    //This is the interrupt request
ISR(TIMER2_COMPA_vect) {   //This is the interrupt request
  timer++;
}