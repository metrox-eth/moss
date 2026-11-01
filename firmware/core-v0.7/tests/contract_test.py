# SPDX-License-Identifier: Apache-2.0
"""Mutation checks for the independent contract validator; never edits authoritative inputs."""
import copy,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tools'))
from contract_paths import electrical_path
electrical=electrical_path(root)
base=json.loads((electrical/'circuit.json').read_text())
base_map=json.loads((electrical/'MCU_PIN_MAP.json').read_text())
cases=root/'fw_build/contract_cases';cases.mkdir(exist_ok=True)
for case in ('both_gpio_maps_changed','wrong_adc_address','wrong_uart_oe_part','wrong_shunt'):
    circuit=copy.deepcopy(base);pinmap=copy.deepcopy(base_map);parts={p['ref']:p for p in circuit['parts']}
    if case=='both_gpio_maps_changed':
        parts['U1']['pins']['39'][0]='IO2';pinmap['pins']['39'][0]='IO2'
    elif case=='wrong_adc_address':parts['U43']['pins']['1'][1]='3V3'
    elif case=='wrong_uart_oe_part':parts['U14']['mpn']='SN74LVC2G125DCUR'
    elif case=='wrong_shunt':parts['R180']['value']='1mR 1% 5W'
    dest=cases/case;dest.mkdir(exist_ok=True)
    (dest/'circuit.json').write_text(json.dumps(circuit));(dest/'MCU_PIN_MAP.json').write_text(json.dumps(pinmap))
    result=subprocess.run([sys.executable,str(root/'tools/validate_contract.py'),'--electrical',str(dest)],capture_output=True,text=True)
    assert result.returncode!=0,case
print('PASS 4 contract mutations rejected: both GPIO maps, ADC address, OE polarity part, shunt value')
