"""Check the MOSS rearm contract and native KiCad XML; not analog SPICE.

Examples:
  python3 test_variant.py --circuit electrical/circuit.json --netlist NETLIST.xml \
      --output LOGIC_TEST_RESULTS.json
  python3 test_variant.py --design . --output LOGIC_TEST_RESULTS.json

Export the XML first with kicad-cli sch export netlist --format kicadxml.
The optional --design directory can contain electrical/ or be electrical/ itself.
No earlier proposal, CONTRACT_PATCH file, or workstation-specific path is required.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,itertools,json,xml.etree.ElementTree as ET

parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--design',type=Path,help='Design directory containing circuit.json or electrical/circuit.json')
parser.add_argument('--circuit',type=Path,help='Current circuit.json contract')
parser.add_argument('--netlist',type=Path,help='Current native KiCad XML netlist, exported with --format kicadxml')
parser.add_argument('--output',type=Path,default=Path('LOGIC_TEST_RESULTS.json'),help='JSON report destination')
args=parser.parse_args()
if args.design:
    root=args.design
    electrical=root/'electrical' if (root/'electrical/circuit.json').is_file() else root
    args.circuit=args.circuit or electrical/'circuit.json'
    if args.netlist is None:
        options=[root/'NETLIST.xml',electrical/'NETLIST.xml',root/'evidence/NETLIST.xml']
        args.netlist=next((p for p in options if p.is_file()),None)
if args.circuit is None or args.netlist is None:
    parser.error('Supply --circuit and --netlist, or --design containing both current files.')
for p in [args.circuit,args.netlist]:
    if not p.is_file():parser.error('Input does not exist: '+str(p))
d=json.loads(args.circuit.read_text())
parts={p['ref']:p for p in d['parts']}
net=lambda r,p:parts[r]['pins'][str(p)][1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
UNKNOWN=None
GUARD_NS=1000.0
MIN_PULSE_NS=2.7
RECOVERY_MIN_NS=1.2

def check(x,message):
    if not x:raise AssertionError(message)

physical={('U51',1):'ARM_COMMIT_CLK',('U51',2):'3V3',('U51',3):None,
 ('U51',4):'GND',('U51',5):'ARM_LATCHED',('U51',6):'ARM_CLEAR_N',
 ('U51',7):'3V3',('U51',8):'3V3',('U1',39):'ARM_COMMIT',('U1',38):'ARM_LATCHED',
 ('U6',1):'WD_ENABLE',('U6',4):'ARM_READY',('U6',5):'RESET_N',
 ('U6',9):'WD_ENABLE',('U6',12):'ARM_READY',('U6',13):'RESET_N',
 ('U52',1):'ACT_READY',('U52',2):'RESET_N',('U52',13):'WD_ENABLE',('U52',12):'ARM_CLEAR_BASE',
 ('U52',3):'ARM_CLEAR_BASE',('U52',4):'ACT_POWER_ENABLE',('U52',5):'3V3',('U52',6):'ARM_CLEAR_N',
 ('U52',9):'ACT_READY',('U52',10):'ARM_LATCHED',('U52',11):'ACT_POWER_ENABLE',('U52',8):'ARM_READY',
 ('U52',7):'GND',('U52',14):'3V3'}
for k,v in physical.items():check(net(*k)==v,'Pin role '+str(k))
check(parts['U51']['mpn']=='SN74LVC1G74DCUR','DFF exact MPN')
check(parts['U52']['mpn']=='SN74HCS11PWR','Slow-input-qualified exact MPN')
check(parts['U6']['mpn']=='SN74HCS21PWR','Existing four-input AND gate MPN')
check(parts['U11']['mpn']=='74LV08APWJ','Existing motor-command AND gate MPN')
check(net('U51',1)!=net('U1',29),'UART packet enable must not clock latch')
for r,pair in {'R228':{'ARM_COMMIT_CLK','GND'},'R229':{'ARM_LATCHED','GND'},
               'R230':{'ARM_COMMIT','ARM_COMMIT_CLK'}}.items():
    check({v[1]for v in parts[r]['pins'].values()}==pair,r+' route')
for r,mpn in {'R228':'RC0603FR-0710KL','R229':'RC0603FR-07100KL','R230':'RC0603FR-07100RL',
              'C154':'GRM188R71C104KA01D','C155':'GRM188R71C104KA01D'}.items():
    check(parts[r]['mpn']==mpn,r+' reviewed exact MPN/value')
for r in ['C154','C155']:
    check({v[1]for v in parts[r]['pins'].values()}=={'3V3','GND'},r+' decoupling rails')

# Load pin functions from the proposed physical device mappings.
gates=[]
for ref,units in [('U52',[([1,2,13],12),([3,4,5],6),([9,10,11],8)]),
                  ('U6',[([1,2,4,5],6),([9,10,12,13],8)]),
                  ('U11',[([1,2],3),([4,5],6),([9,10],8),([12,13],11)])]:
    for inputs,output in units:gates.append((ref,[net(ref,p)for p in inputs],net(ref,output)))

def and3(values):
    if any(v is False for v in values):return False
    if any(v is UNKNOWN for v in values):return UNKNOWN
    return True

def evaluate(flags,q,commands=None):
    states={'3V3':True,'GND':False,'ARM_LATCHED':q,**flags,
            **(commands or {'PWM_L':True,'PWM_R':True,'DIR_L':False,'DIR_R':True})}
    for ref,inputs,output in gates:states[output]=and3([states[p]for p in inputs])
    j2={}
    for r,pin in [('R23',1),('R25',2),('R27',3),('R29',4)]:
        states[net(r,2)]=states[net(r,1)]
        j2[str(pin)]=states[net('J2',pin)]
    return states,j2

FAULTS=['ACT_READY','RESET_N','WD_ENABLE','ACT_POWER_ENABLE']
ALL_GOOD={k:True for k in FAULTS+['DRIVE_ENABLE','SERVO_TX_ENABLE']}

class Latch:
    def __init__(self,q=False,clock=False,clear=False):
        self.q=q if clear else False;self.clock=clock;self.clear=clear
        self.last_clock_edge=-1e12;self.last_rise=-1e12
        self.clear_asserted=-1e12;self.clear_released=-1e12
        self.issues=[]
    def step(self,t,flags,clock,powered=True):
        if not powered:
            self.q=UNKNOWN;self.clock=clock;self.clear=False
            self.clear_asserted=t
            return {'time_ns':t,'q':self.q,'logic_power_valid':False}
        before,_=evaluate(flags,self.q)
        clear=before[net('U51',6)]
        rising=clock and not self.clock;falling=self.clock and not clock
        event_issues=[]
        if not clear:
            if self.clear:self.clear_asserted=t
            self.q=False
        else:
            if not self.clear:
                self.clear_released=t
                if t-self.clear_asserted<MIN_PULSE_NS:event_issues.append('clear pulse below2.7ns')
                # Manufacturer provides no independent removal guarantee.
                # A deliberately broad protocol guard classifies near-coincidences
                # as unqualified instead of inventing a removal time.
                if t-self.last_clock_edge<GUARD_NS:event_issues.append('clear release near prior clock edge; removal unqualified')
            if rising:
                if t-self.clear_released<GUARD_NS:event_issues.append('clock inside clear-release guard')
                if t-self.last_clock_edge<MIN_PULSE_NS:event_issues.append('clock low pulse below2.7ns')
                if not event_issues:self.q=True  # D is physically tied to3V3.
            if falling and t-self.last_rise<MIN_PULSE_NS:event_issues.append('clock high pulse below2.7ns')
            if event_issues:self.q=UNKNOWN
        if rising:self.last_rise=t
        if rising or falling:self.last_clock_edge=t
        self.clock=clock;self.clear=clear
        self.issues.extend({'time_ns':t,'reason':reason}for reason in event_issues)
        states,j2=evaluate(flags,self.q)
        return {'time_ns':t,'clock':clock,'clear_n':clear,'q':self.q,'flags':dict(flags),
                'DRIVE_RUN':states['DRIVE_RUN'],'SERVO_OE_ON':states['SERVO_OE_ON'],
                'J2':j2,'timing_issues':event_issues,'logic_power_valid':True}

# Combined signal qualification from actual pin maps, including the new latch.
combinations=0
for bits in itertools.product([False,True],repeat=11):
    flags=dict(zip(FAULTS+['DRIVE_ENABLE','SERVO_TX_ENABLE'],bits[:6]));q=bits[6]
    commands=dict(zip(['PWM_L','PWM_R','DIR_L','DIR_R'],bits[7:]))
    states,j2=evaluate(flags,q,commands)
    prerequisites=all(flags[n]for n in FAULTS) and q
    drive=prerequisites and flags['DRIVE_ENABLE'];uart=prerequisites and flags['SERVO_TX_ENABLE']
    check(states['DRIVE_RUN']==drive,'Drive predicate')
    check(states['SERVO_OE_ON']==uart,'UART predicate')
    for p,raw in [(1,'PWM_L'),(2,'DIR_L'),(3,'PWM_R'),(4,'DIR_R')]:
        check(j2[str(p)]==(drive and commands[raw]),'J2 command mask')
    combinations+=1

# Every old/new fault combination and clock transition; invalid release/clock
# coincidences are counted as unqualified, not as proof of a safe output.
transitions=0;unqualified=0
for q,old_clock,old_bits,new_bits,new_clock in itertools.product(
        [False,True],[False,True],list(itertools.product([False,True],repeat=4)),
        list(itertools.product([False,True],repeat=4)),[False,True]):
    old_flags={**ALL_GOOD,**dict(zip(FAULTS,old_bits))};flags={**ALL_GOOD,**dict(zip(FAULTS,new_bits))}
    old_clear=all(old_bits);model=Latch(q,old_clock,old_clear)
    row=model.step(10000,flags,new_clock)
    if not all(new_bits):check(row['q'] is False,'Async fault dominates clock')
    elif not old_clear and new_clock and not old_clock:
        check(row['q'] is UNKNOWN and row['timing_issues'],'Coincidence must not be called safe')
        unqualified+=1
    else:
        expected=True if new_clock and not old_clock else (q if old_clear else False)
        check(row['q']==expected,'Valid clock/hold transition')
    transitions+=1

scenarios=[]
for fault,held_clock in itertools.product(FAULTS,[False,True]):
    model=Latch(True,held_clock,True)
    bad={**ALL_GOOD,fault:False}
    rows=[model.step(10000,bad,held_clock),model.step(20_000_000,ALL_GOOD,held_clock)]
    check(all(x['q'] is False and x['DRIVE_RUN'] is False and x['SERVO_OE_ON'] is False for x in rows),
          'Held GPIO must not restart after '+fault)
    rows.append(model.step(21_000_000,ALL_GOOD,False))
    rows.append(model.step(22_000_000,ALL_GOOD,True))
    check(rows[-1]['q'] is True,'Fresh post-qualification pulse must permit arm')
    check(not model.issues,'Valid protocol timing')
    scenarios.append({'name':'fault_recovery_held_clock','fault':fault,'held_clock':held_clock,'trace':rows})

# Boot without an impossible dependency on the still-unpowered actuator rail.
model=Latch(False,True,False)
boot=[model.step(10000,{**ALL_GOOD,'RESET_N':False,'ACT_READY':False,'ACT_POWER_ENABLE':False,'WD_ENABLE':False},True),
      model.step(20_000_000,{**ALL_GOOD,'ACT_READY':False},True),
      model.step(40_000_000,ALL_GOOD,True),model.step(41_000_000,ALL_GOOD,False),model.step(42_000_000,ALL_GOOD,True)]
check(boot[1]['flags']['ACT_POWER_ENABLE'] and boot[1]['q'] is False,'Rail establishment before ready allowed')
check(boot[2]['q'] is False and boot[-1]['q'] is True,'No boot rearm from retained high clock')
scenarios.append({'name':'boot_and_first_explicit_arm','trace':boot})

model=Latch(False,False,False);bad={**ALL_GOOD,'ACT_READY':False}
ignored=[model.step(10000,bad,True),model.step(20_000_000,ALL_GOOD,True)]
check(ignored[-1]['q'] is False,'Pulse during fault must not replay on clear release')
scenarios.append({'name':'arm_pulse_during_fault_held_high_afterwards','trace':ignored})

model=Latch(False,False,True);packets=[]
for i in range(20):
    packets.append(model.step(10000*(i+1),{**ALL_GOOD,'SERVO_TX_ENABLE':bool(i%2)},False))
check(all(x['q'] is False and x['SERVO_OE_ON'] is False for x in packets),'UART packet pulses must never arm')
scenarios.append({'name':'UART_packet_enable_is_not_clock','trace':packets})

model=Latch(False,False,False)
row=model.step(10000,ALL_GOOD,True)
check(row['q'] is UNKNOWN and row['timing_issues'],'Release/clock coincidence is unqualified')
scenarios.append({'name':'deliberately_invalid_clear_release_clock_coincidence','expected':'UNQUALIFIED','trace':[row]})

model=Latch(False,False,True)
short=[model.step(10000,ALL_GOOD,True),model.step(10001,ALL_GOOD,False)]
check(short[-1]['q'] is UNKNOWN,'Sub-minimum clock pulse not guaranteed')
scenarios.append({'name':'deliberately_invalid_one_ns_clock_pulse','expected':'UNQUALIFIED','trace':short})

model=Latch(True,True,True)
restart=[model.step(10000,ALL_GOOD,True,powered=False),
         model.step(20_000_000,{**ALL_GOOD,'RESET_N':False},True),model.step(40_000_000,ALL_GOOD,True)]
check(restart[0]['q'] is UNKNOWN and restart[1]['q'] is False and restart[2]['q'] is False,'Post-valid-supply reset must clear before release')
scenarios.append({'name':'power_invalid_then_qualified_reset','trace':restart})

# Native schematic netlist parity, including exact NC export semantics.
xml=ET.parse(args.netlist).getroot();pins={};metadata={}
for item in xml.findall('./nets/net'):
    for node in item.findall('node'):
        key=(node.get('ref'),node.get('pin'));check(key not in pins,'Duplicate netlist pin')
        pins[key]=item.get('name');metadata[key]=(len(item.findall('node')),node.get('pintype',''))
expected_keys={(p['ref'],str(pin))for p in d['parts']for pin in p['pins']}
check(set(pins).issubset(expected_keys),'Native netlist contains physical pins absent from current contract')
pin_count=0
for p in d['parts']:
    for pin,data in p['pins'].items():
        actual=pins.get((p['ref'],pin));expected=data[1]
        if expected is None and actual is not None:
            count,typ=metadata[(p['ref'],pin)]
            check(actual.startswith('unconnected-') and count==1 and 'no_connect'in typ,'Unexpected NC connection')
        else:check(actual==expected,f'Variant netlist pin {p["ref"]}.{pin}')
        pin_count+=1

report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status':'CONTRACT_LOGIC_MODEL_PASS_WITH_EXPLICIT_TIMING_LIMITS',
 'inputs':{'circuit_file':args.circuit.name,'netlist_file':args.netlist.name},
 'circuit_sha256':sha(args.circuit),'native_netlist_sha256':sha(args.netlist),
 'script_sha256':sha(Path(__file__)),'counts':{'static_command_combinations':combinations,'state_transitions':transitions,
   'unqualified_coincident_transitions':unqualified,'native_physical_pin_definitions':pin_count,'sequence_scenarios':len(scenarios)},
 'gate_models':gates,'scenarios':scenarios,
 'timing':{'supply_nominal_V':3.384,'DFF_table_supply_range_V':[3.0,3.6],
   'DFF_min_clear_low_ns':MIN_PULSE_NS,'DFF_min_clock_high_low_ns':MIN_PULSE_NS,'DFF_clear_release_setup_before_clock_ns':RECOVERY_MIN_NS,
   'DFF_separate_clear_removal_spec_ns':None,'DFF_max_input_slew_ns_per_V':10,
   'model_protocol_guard_ns':GUARD_NS,'recommended_GPIO_pulse_ns':1_000_000,
   'note':'Guard is a conservative protocol choice, not a fabricated manufacturer removal specification. Near-coincidences and out-of-range supply are explicitly unqualified.'},
 'guarantee':'After a valid ACT_READY/RESET_N/WD_ENABLE/ACT_POWER_ENABLE low clears U51, restoring those levels or old PWM/TX_ENABLE levels cannot restore permission without a new qualified rising edge on the dedicated ARM_COMMIT clock.',
 'limits':['Current contract/native netlist logic check only; no PCB copper connectivity, routed slew or hardware test.',
 'Digital Boolean/state model, not transistor SPICE, EMI, analog brownout, metastability probability, contact bounce or real motor/servo simulation.',
 'No guarantee for a clock edge inside asynchronous-clear recovery/removal uncertainty. The protocol must hold clock low during qualification and wait before pulsing.',
 'The circuit recognizes a new electrical ARM_COMMIT edge; firmware must discard queued old arm events and must never clock this signal per UART packet.',
 'ACT_POWER_ENABLE remains upstream; the latch inhibits new motor PWM/DIR and UART transmission, not actuator power or autonomous behaviour of an already-commanded/restarting servo.',
 'Unpowered Cytron braking/regeneration and supply transients remain outside the model.']}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'counts':report['counts'],
                 'circuit_sha256':report['circuit_sha256'],'native_netlist_sha256':report['native_netlist_sha256']},indent=2))
