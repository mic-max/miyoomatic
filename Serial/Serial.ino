// Dumb solenoid driver. This sketch owns no timing and keeps no state between bytes --
// the PC decides exactly when every button goes down and comes back up.
//
// Protocol: one byte per action, no framing, no terminator.
//   bit 7     1 = press (drive HIGH), 0 = release (drive LOW)
//   bits 0-3  solenoid index, 0..7
//   bits 4-6  unused, must be 0
//
//   0x80 -> solenoid 0 down      0x00 -> solenoid 0 up
//   0x87 -> solenoid 7 down      0x07 -> solenoid 7 up
//
// A tap is two bytes (0x80 then 0x00) sent with whatever gap the PC wants; a hold is the
// same two bytes further apart; a chord is several presses before any release.
// Bytes naming an index we have no pin for are ignored and not echoed, so a garbled byte
// can never drive something that isn't wired.

#define SolenoidCount 8
#define PressBit 0x80
#define IndexMask 0x0F

const int solenoids[SolenoidCount] = {2, 3, 4, 5, 6, 7, 8, 9};

void setup()
{
    // 115200 puts a byte on the wire in ~87us, down from ~1ms at 9600. That transfer time
    // is the floor on how precisely the PC can place a press edge, so it is the single
    // biggest lever on responsiveness here. The PC side must match: baud is hardcoded in
    // ArduinoController.__init__ (pc/src/controllers.py) and both ends have to agree.
    Serial.begin(115200);

    // Consider printing a one-line boot banner here (Serial.println("READY")) once the PC
    // side is ready to consume it. The Nano auto-resets when the port is opened, so today
    // the PC has to sleep a guessed ~2s and hope no early bytes get swallowed during the
    // bootloader window. A banner turns that guess into a definite "the board is up now"
    // signal, and it also distinguishes a freshly-reset board from a wedged one.

    for (int i = 0; i < SolenoidCount; i++)
    {
        pinMode(solenoids[i], OUTPUT);
        digitalWrite(solenoids[i], LOW);
    }
}

void loop()
{
    // Spin rather than delay(). There is nothing else for this chip to do, so polling flat
    // out makes the worst-case gap between a byte landing in the UART buffer and the pin
    // moving one loop() iteration (microseconds) instead of one sleep interval.
    if (!Serial.available())
    {
        return;
    }

    int b = Serial.read();
    if (b < 0)
    {
        return; // can't happen after available(), but read() is documented to allow it
    }

    int index = b & IndexMask;
    if (index >= SolenoidCount)
    {
        return; // no such solenoid; stay quiet so the PC sees the dropped echo
    }

    // Nothing here caps how long a solenoid stays energized. If the PC crashes or the USB
    // cable is pulled between a press and its release, the coil sits hot until someone
    // unplugs it. That protection belongs on the PCB/hardware side rather than as timing
    // logic added back into this sketch.
    digitalWrite(solenoids[index], (b & PressBit) ? HIGH : LOW);

    Serial.write(b); // echo exactly what we acted on
}
