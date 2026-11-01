#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include "Core.h"
#include "Sensors.h"
#include "Feetech.h"
using namespace core07;
static unsigned checks=0;
#define VERIFY(c) do { ++checks; assert(c); } while(0)

// Actual usbOpen/serviceTx bodies are extracted without rewriting expressions.
struct SerialStub { bool open=true; explicit operator bool()const{return open;} } Serial;
bool mounted=true,suspended=false;
bool tud_mounted(){return mounted;}
bool tud_suspended(){return suspended;}
char txQueue[4096]{};size_t txHead=0,txTail=0;
unsigned writeCalls=0,flushCalls=0,offered=0,acceptLimit=0;
uint32_t tud_cdc_n_write(unsigned,const void*,uint32_t n){++writeCalls;offered=n;return n<acceptLimit?n:acceptLimit;}
void tud_cdc_n_write_flush(unsigned){++flushCalls;}
#include "usb_functions.inc"

struct AdcBus {
  uint16_t raw;
  bool read(uint8_t address,uint8_t reg,uint16_t& value){VERIFY(address==0x48&&reg==0);value=raw;return true;}
  bool write(uint8_t,uint8_t,uint16_t){return false;}
};
int main(){
  Lines lines;
  std::string command="servo syncmove";
  for(int id=247;id<=253;id++)command+=" "+std::to_string(id)+" 4095 1500 254";
  VERIFY(command.size()==140);VERIFY(sizeof(lines.data)>=command.size()+1);
  for(char c:command)VERIFY(lines.push(c,100)==0);
  VERIFY(lines.push('\n',100)==1);VERIFY(command==lines.data);

  feetech::Goal goals[8]{};
  for(unsigned j=0;j<7;j++)goals[j]={uint8_t(247+j),4095,1500,254};
  uint8_t parameters[58]{},wire[feetech::CAP]{};
  VERIFY(feetech::syncArgs(goals,7,parameters)==58);
  VERIFY(parameters[0]==41&&parameters[1]==7);
  for(unsigned j=0;j<7;j++){
    size_t at=2+j*8;
    VERIFY(parameters[at]==247+j);VERIFY(parameters[at+1]==254);
    VERIFY(parameters[at+2]==255&&parameters[at+3]==15);
    VERIFY(parameters[at+4]==0&&parameters[at+5]==0);
    VERIFY(parameters[at+6]==220&&parameters[at+7]==5);
  }
  VERIFY(feetech::packet(254,0x83,parameters,58,wire)==64);
  VERIFY(wire[2]==254&&wire[3]==60&&wire[4]==0x83);
  uint8_t sum=0;for(unsigned j=2;j<64;j++)sum+=wire[j];VERIFY(sum==255);
  VERIFY(feetech::syncArgs(goals,1,parameters)==0);
  VERIFY(feetech::syncArgs(goals,8,parameters)==0);
  goals[1].id=goals[0].id;VERIFY(feetech::syncArgs(goals,2,parameters)==0);
  VERIFY(feetech::packet(254,3,parameters,1,wire)==0);

  for(int raw : {-1,-80,0,80}){
    Sensors s;s.channel=3;s.adsPhase=2;AdcBus b{uint16_t(int16_t(raw))};
    s.adsStep(b,100);VERIFY(s.analog[3].valid);
    VERIFY(std::fabs(s.analog[3].value-raw*.000125f)<1e-7);
    VERIFY(s.channel==0);
  }
  for(int raw : {-32768,32767}){
    Sensors s;s.channel=3;s.adsPhase=2;AdcBus b{uint16_t(int16_t(raw))};
    s.adsStep(b,100);VERIFY(!s.analog[3].valid&&s.errors==1);
  }
  {Sensors s;s.channel=0;s.adsPhase=2;AdcBus b{65535};s.adsStep(b,100);VERIFY(!s.analog[0].valid);}
  {Sensors s;s.channel=2;s.adsPhase=2;AdcBus b{23200};s.adsStep(b,100);VERIFY(!s.analog[2].valid);}

  for(unsigned bits=0;bits<8;bits++){
    Serial.open=bits&1;mounted=bits&2;suspended=bits&4;
    VERIFY(usbOpen()==(bool(bits&1)&&bool(bits&2)&&!bool(bits&4)));
  }
  Serial.open=true;mounted=true;suspended=false;
  txHead=100;txTail=0;acceptLimit=0;serviceTx();
  VERIFY(writeCalls==1&&flushCalls==1&&txTail==0&&offered==64);
  acceptLimit=17;serviceTx();VERIFY(writeCalls==2&&flushCalls==2&&txTail==17);
  acceptLimit=64;serviceTx();VERIFY(writeCalls==3&&txTail==81);
  Serial.open=false;serviceTx();VERIFY(txHead==0&&txTail==0&&writeCalls==3);
  Safety safety;VERIFY(!safety.faulted());safety.stop("stop");VERIFY(!safety.faulted());
  safety.stop("usb_disconnected");VERIFY(safety.faulted());
  printf("PASS %u independent delta assertions: SyncWrite bounds, signedAIN3, USB suspend/nonblocking output, LED reason\n",checks);
}
