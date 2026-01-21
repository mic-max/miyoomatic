#define WaitOnSerialMs 20
#define SolenoidActiveMs 40

const int solenoids[4] = {2, 3, 4, 5};

void setup()
{
    Serial.begin(9600);
    for (int i = 0; i < 4; i++)
    {
        pinMode(solenoids[i], OUTPUT);
        digitalWrite(solenoids[i], LOW);
    }
}

void loop()
{
    if (!Serial.available())
    {
        delay(WaitOnSerialMs);
        return;
    }

    int index = Serial.read() - '0'; // expect '0'..'3'

    if (index < 0 || index >= 4)
    {
        return; // invalid command
    }

    int pin = solenoids[index];

    digitalWrite(pin, HIGH);
    delay(SolenoidActiveMs);
    digitalWrite(pin, LOW);
    Serial.write(index);
}
