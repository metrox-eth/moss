#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent assertions against both hardware JSONs and firmware constants. No generated oracle."""
import argparse,json,re,hashlib
from pathlib import Path
from contract_paths import electrical_path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--electrical',type=Path);a=p.parse_args();a.electrical=electrical_path(root,a.electrical)
parts=json.loads((a.electrical/'circuit.json').read_text())['parts'];parts={x['ref']:x for x in parts}
mp=json.loads((a.electrical/'MCU_PIN_MAP.json').read_text())
assert parts['U1']['pins']==mp['pins'],'MCU map diverges from circuit'
assert parts['U1']['mpn']=='ESP32-S3-WROOM-1U-N8'
# Human-reviewed map, deliberately independent of generated header and circuit traversal.
expected={'ESTOP_ACTIVE':4,'ENC_R_A':5,'ENC_L_B':6,'ENC_L_A':7,'STATUS_LED':15,'ENC_R_B':16,'DIR_L':17,'PWM_L':18,'DIR_R':8,'PWM_R':9,'AUDIO_BCLK':10,'AUDIO_LRCLK':11,'AUDIO_DATA':12,'AUDIO_ENABLE':13,'USB_PWR_FAULT_N':14,'DRIVE_ENABLE':21,'WD_ENABLE':47,'WD_TICK':48,'SERVO_TX':35,'SERVO_TX_ENABLE':36,'SERVO_RX':37,'ACT_POWER_ENABLE':38,'ACT_READY':39,'I2C_SCL':40,'I2C_SDA':41,'ENC_POWER_EN':42,'DRIVE_RUN':44,'DEBUG_TX':43,'ARM_LATCHED':2,'ARM_COMMIT':1,'ESP_USB_N':19,'ESP_USB_P':20,'BOOT_N':0}
observed={v[1]:int(re.match(r'IO(\d+)',v[0])[1]) for v in parts['U1']['pins'].values() if v[0].startswith('IO') and v[1]}
header=dict((k,int(v)) for k,v in re.findall(r'([A-Z][A-Z0-9_]*)\s*=\s*(\d+)',(root/'src/MOSS_CORE_V07/Pins.h').read_text()))
assert observed==expected,'GPIO contract differs from reviewed map';assert header==expected,'Firmware header differs from reviewed map';assert len(set(header.values()))==len(header)
def pin(ref,num,name,net):
 assert parts[ref]['pins'][str(num)][:2]==[name,net],f'{ref}.{num}: expected {name}->{net}'
def mpn(ref,value):assert parts[ref]['mpn']==value,f'{ref} component changed'
mpn('U5','TPS3431SDRBR');pin('U5',3,'EN','3V3');pin('U5',5,'SET1','WD_ENABLE');pin('U5',6,'WDI','WD_TICK')
mpn('U14','SN74LVC2G126DCUR');pin('U14',1,'1OE','SERVO_OE_ON');pin('U14',2,'1A','SERVO_TX');pin('U14',6,'1Y','SERVO_TX_BUF')
mpn('U17','INA226AIDGSR');pin('U17',1,'A1','GND');pin('U17',2,'A0','GND');pin('U17',8,'VBUS','PACK_VBUS');pin('U17',9,'IN_MINUS','GND');pin('U17',10,'IN_PLUS','GND')
mpn('U43','ADS1115IDGSR');pin('U43',1,'ADDR','GND');pin('U43',4,'AIN0','CURRENT_L_ADC');pin('U43',5,'AIN1','CURRENT_R_ADC');pin('U43',6,'AIN2','3V3');pin('U43',7,'AIN3','GND')
for ref,out in [('U40','CURRENT_L_RAW'),('U41','CURRENT_R_RAW')]:
 mpn(ref,'INA240A2PWR');pin(ref,6,'REF2','GND');pin(ref,7,'REF1','3V3');pin(ref,8,'OUT',out)
mpn('U23','MAX98357AETE+T');pin('U23',4,'SD_MODE','AMP_ENABLE')
mpn('U51','SN74LVC1G74DCUR');pin('U51',1,'CLK','ARM_COMMIT_CLK');pin('U51',5,'Q','ARM_LATCHED')
for net in ['CURRENT_L_RAW','CURRENT_R_RAW']:
 assert any(x.get('value','').startswith('470') and any(v[1]==net for v in x['pins'].values()) for x in parts.values())
shunts=[x for x in parts.values() if x.get('value','').startswith('2m')]
assert len(shunts)==2,[(x['ref'],x['value']) for x in shunts]
for ref,side in [('R180','L'),('R181','R')]:
 assert parts[ref]['value']=='2mR 1% 5W'
 pin(ref,1,'I_FROM_CYTRON',f'CYTRON_{side}_LEAD');pin(ref,2,'I_TO_MOTOR',f'MOTOR_{side}_LEAD')
print(json.dumps({'status':'PASS','gpio_count':len(expected),'parts_checked':len(parts),'sha256':{n:hashlib.sha256((a.electrical/n).read_bytes()).hexdigest() for n in ['circuit.json','MCU_PIN_MAP.json']}},indent=2))
