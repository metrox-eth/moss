#include <assert.h>
#include "../MOSS_QTPY_MDD3A/MOSS_QTPY_MDD3A.ino"

void command(const char* text) {
  char line[128]; strcpy(line,text); Serial.output.clear(); handleCommand(line);
}
void zeroOutputs() {
  assert(stubPwm[M1A]==0 && stubPwm[M1B]==0 && stubPwm[M2A]==0 && stubPwm[M2B]==0);
  assert(control.mode==moss::OFF && control.left==0 && control.right==0);
  assert(rampL.value==0 && rampR.value==0);
}
int main() {
  stubInput(STOP_NC,LOW); setup();
  assert(!stopLoop.blocked());
  command("arm"); command("drive 50 50");
  stubNow+=31; loop();
  assert((stubPwm[M1A]>0 || stubPwm[M1B]>0) && (stubPwm[M2A]>0 || stubPwm[M2B]>0));

  stubInput(STOP_NC,HIGH); loop(); zeroOutputs();
  for (const char* cmd : {"arm","drive 100 100","test left 100","test right -100"}) {
    command(cmd); assert(Serial.output=="ERR stop_latched\n"); zeroOutputs();
  }
  command("clearstop"); assert(Serial.output=="ERR stop_open\n"); zeroOutputs();
  command("status"); assert(Serial.output.find("\"stop_open\":true")!=std::string::npos);
  stubInput(STOP_NC,LOW); loop();
  stubNow=stopLoop.closedSince+99; command("clearstop");
  assert(Serial.output=="ERR stop_not_stable\n"); zeroOutputs();
  stubNow+=1; command("arm");
  assert(Serial.output=="ERR stop_latched\n"); zeroOutputs();
  command("clearstop"); assert(Serial.output=="OK\n"); zeroOutputs();
  command("drive 50 50"); assert(Serial.output=="ERR not_armed\n"); zeroOutputs();

  command("arm"); command("drive 50 50"); stubNow+=31; loop();
  assert((stubPwm[M1A]>0 || stubPwm[M1B]>0) && (stubPwm[M2A]>0 || stubPwm[M2B]>0));
  // A complete open/close pulse between polls is retained by the rising-edge ISR.
  stubInput(STOP_NC,HIGH); stubInput(STOP_NC,LOW); loop();
  assert(stopLoop.latched && !stopLoop.open); zeroOutputs();
  command("clearstop"); assert(Serial.output=="ERR stop_not_stable\n");
  stubNow+=100; command("clearstop"); zeroOutputs();
  // Check the serial dispatcher, not just calls to the command handler.
  Serial.input="arm\ndrive 50 50\n"; loop(); stubNow+=31; loop();
  assert((stubPwm[M1A]>0 || stubPwm[M1B]>0) && (stubPwm[M2A]>0 || stubPwm[M2B]>0));
  stubInput(STOP_NC,HIGH);
  Serial.input="arm\ntest left 100\ndrive 100 100\n"; loop(); zeroOutputs();
  assert(stopLoop.latched);
  // A controller restart while the button is held or its wire is open stays off.
  control={}; stopLoop={}; stopEdgeSeen=false; setup(); zeroOutputs();
  assert(stopLoop.open && stopLoop.latched);
  command("arm"); assert(Serial.output=="ERR stop_latched\n"); zeroOutputs();
  puts("qtpy_stop_integration_test: OK (GPIO, IRQ, serial commands, PWM and ramp reset, boot)");
}
