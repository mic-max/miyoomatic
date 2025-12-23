enum Commands {
  Up, Down, Left, Right,
  A, B, X, Y,
  L, R, L2, R2,
  Select, Start,
  PrintScreen, Wait
};

#define SolenoidActiveMs 40
#define WaitOnSerialMs 20
#define Screenshot 's'
#define Resume 'r'

const int solenoids[4] = {2, 3, 4, 5};

int buttonMap[14] = {0};
int sweetScentButtons[4] = {Down, Right, Start, A};
int sweetScent[12][2] = {
  {      Start,  300}, // open menu, can maybe press twice, but no spamming.
  {          A, 1000}, // select pokemon menu item, can spam
  {          A,  200}, // select first slot pokemon
  {       Down,  200}, // navigate to sweet scent
  {          A, 9500}, // use sweet scent, can spam
  {PrintScreen,   -1}, // over serial: tell PC to take a photo
  {          A, 2800}, // skip dialog, can spam
  {       Down,  200}, // hover pokemon, can spam
  {      Right,  200}, // hover run, can spam
  {       Wait,   -1}, // wait for a message over serial
  {          A,  600}, // run, can spam
  {          A, 2800}, // skip dialog, can spam
};
int incomingByte = 0;
int currentIndex = 0;
const int scriptLen = sizeof(sweetScent) / sizeof(sweetScent[0]);

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < 4; i++) {
    pinMode(solenoids[i], OUTPUT);
    buttonMap[sweetScentButtons[i]] = solenoids[i];
  }
}

void loop() {
  int command = sweetScent[currentIndex][0];

  switch (command) {
  case PrintScreen:
    Serial.println(Screenshot); // TODO: print or println or print with a flush?
    break;
  case Wait:
    while (!Serial.available()) {
      // TODO: replace the button code with letting me send button presses over PuTTY
      // once a final char is sent like enter, resume command processing and that terminates this Wait command job
      delay(WaitOnSerialMs);
    }
    incomingByte = Serial.read(); // Wait for resume command

    if (incomingByte != Resume) {
     Serial.println("TERMINATING, I RECVD INVALID RESUME BYTE");
     return -2; // Received an invalid byte
    }
    break;
  default:
    int solenoidPin = buttonMap[command];
    int sleepMs = sweetScent[currentIndex][1]; // TODO: multiply this value by the number of milliseconds per update and the speedup
    if (!solenoidPin) {
      // TODO: print error over serial.
      return -1; // No solenoid is assigned to that command
    }

    digitalWrite(solenoidPin, HIGH);
    delay(SolenoidActiveMs);
    digitalWrite(solenoidPin, LOW);
    delay(sleepMs);
    break;
  }

  currentIndex = (currentIndex + 1) % scriptLen;
}
