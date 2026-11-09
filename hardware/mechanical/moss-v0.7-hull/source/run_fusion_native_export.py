"""Run the native R92-based hull recipe through Fusion's enabled local MCP API."""
from pathlib import Path
import argparse, json, shutil, urllib.request

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--endpoint',default='http://127.0.0.1:27182/mcp')
    args=parser.parse_args()
    recipe=ROOT/'source/FusionV07Hull/FusionV07Hull.py'
    script='from pathlib import Path\nBASE='+repr(str(ROOT))+'\n'
    script+="env={'MOSS_MECHANICAL_ROOT':BASE,'__file__':"+repr(str(recipe))+"}\n"
    script+="exec(compile(Path(env['__file__']).read_text(),env['__file__'],'exec'),env)\n"
    script+="def run(context):\n    env['run'](context)\n"
    headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
    def request(payload):
        req=urllib.request.Request(args.endpoint,data=json.dumps(payload).encode(),headers=headers)
        return urllib.request.urlopen(req,timeout=240)
    response=request({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'MOSS-hull-rebuild','version':'1'}}})
    session=response.headers.get('MCP-Session-Id');response.read()
    if session:headers['MCP-Session-Id']=session
    request({'jsonrpc':'2.0','method':'notifications/initialized'}).read()
    raw=request({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'fusion_mcp_execute','arguments':{'featureType':'script','object':{'script':script,'readOnly':False}}}}).read().decode()
    if raw.startswith('event:'):raw=next(line[6:] for line in raw.splitlines() if line.startswith('data: '))
    result=json.loads(raw)
    if 'error' in result or result.get('result',{}).get('isError'):raise RuntimeError(result)
    generated=ROOT/'cad/Hull_MOSS_V07_NATIVE_MATCHED.f3d'
    assert generated.is_file(),result
    shutil.copy2(generated,ROOT/'cad/Hull_MOSS_V07_Core_74x71_EDITABLE.f3d')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
