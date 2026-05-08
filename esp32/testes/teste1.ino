#include <math.h>

const int motorPin = 25;

int mode = 0;
unsigned long modeTimer = 0;
unsigned long previousMillis = 0;

int intensidade = 0;
bool increasing = true;
float angle = 0;

void setup() {
  ledcAttach(motorPin, 200, 8);
  modeTimer = millis();
}

void loop() {

  unsigned long currentMillis = millis();

  if (currentMillis - modeTimer > 10000) {
    mode++;
    if (mode > 2) mode = 0;
    modeTimer = currentMillis;
  }

  switch(mode) {

    case 0:
      if (increasing) {
        intensidade += 3;
        if (intensidade >= 255) increasing = false;
      } else {
        intensidade -= 3;
        if (intensidade <= 0) increasing = true;
      }
      ledcWrite(motorPin, intensidade);
      delay(10);
      break;

    case 1:
      ledcWrite(motorPin, 255);
      delay(80);
      ledcWrite(motorPin, 0);
      delay(200);
      break;

    case 2:
      float valor = (sin(angle) + 1.0) * 127.5;
      ledcWrite(motorPin, (int)valor);
      angle += 0.15;
      if (angle > 2 * PI) angle = 0;
      delay(15);
      break;
  }
}