"""Call the existing local Fusion MCP endpoint to export the checked STEP."""
from pathlib import Path
import argparse
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--endpoint',default='http://127.0.0.1:27182/mcp')
    args=parser.parse_args()
    headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
    def call(payload):
        request=urllib.request.Request(args.endpoint,data=json.dumps(payload).encode(),headers=headers)
        with urllib.request.urlopen(request,timeout=180) as response:
            if response.headers.get('MCP-Session-Id'):
                headers['MCP-Session-Id']=response.headers['MCP-Session-Id']
            raw=response.read()
            return json.loads(raw) if raw else {}
    call({'jsonrpc':'2.0','id':1,'method':'initialize','params':{
          'protocolVersion':'2024-11-05','capabilities':{},
          'clientInfo':{'name':'MOSS-local-native-CAD','version':'1.0'}}})
    call({'jsonrpc':'2.0','method':'notifications/initialized'})
    script='MOSS_MECHANICAL_ROOT='+repr(str(ROOT))+'\n'+(ROOT/'source/export_native_print_mesh.py').read_text()
    result=call({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{
         'name':'fusion_mcp_execute','arguments':{'featureType':'script','object':{'script':script}}}})
    (ROOT/'evidence/FUSION_NATIVE_PRINT_MCP_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    assert 'error' not in result,result
    assert not result.get('result',{}).get('isError'),result
    for block in result.get('result',{}).get('content',[]):
        if block.get('type')=='text':
            try: detail=json.loads(block['text'])
            except (KeyError,json.JSONDecodeError):continue
            assert detail.get('success') is not False,detail
    assert (ROOT/'evidence/FUSION_NATIVE_PRINT_EXPORT.json').exists()


if __name__=='__main__':
    main()
