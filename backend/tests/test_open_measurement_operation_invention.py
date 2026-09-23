import json
from pathlib import Path
import backend.modules.hexcore.open_measurement_operation_invention as m
from backend.modules.hexcore.recursive_action_language_expansion import ATOM_ID,LATER_PROCEDURE_ID,_invent_atom

def test_measurement_invention_transfer_delay_and_restart(tmp_path: Path,monkeypatch)->None:
    atom,_=_invent_atom(); atoms=tmp_path/'atoms.json'; atoms.write_text(json.dumps({'atoms':{ATOM_ID:{'spec':atom,'implementation_sha256':m._sha(atom),'authority':LATER_PROCEDURE_ID}}}))
    rows=b''.join(f'{y}-01-01,{y-2000}\n'.encode() for y in range(2001,2011)); payloads={'worldbank':(json.dumps([{'page':1},[{'date':str(y),'value':y-2000} for y in range(2001,2011)]]).encode(),'application/json'),'fred':(b'observation_date,GDP\n'+rows,'text/csv'),'noaa':(b'DATE,TEMP\n'+rows,'text/csv'),'treasury':(b'{"data":['+b','.join(f'{{"record_date":"{y}-01-01","exchange_rate":"{y-2000}"}}'.encode() for y in range(2001,2011))+b']}','application/json')}
    def get(url):
        key='worldbank' if 'worldbank' in url else 'fred' if 'fred' in url else 'noaa' if 'noaa' in url else 'treasury'; body,ct=payloads[key]; return {'status':200,'body':body,'content_type':ct,'url':url}
    monkeypatch.setattr('backend.modules.hexcore.open_property_language_invention._get',get)
    private,registry,state,result=(tmp_path/n for n in ('private.json','registry.json','state.json','result.json'))
    out=m.run(atom_registry_path=atoms,private_measurement_path=private,measurement_registry_path=registry,state_path=state,result_path=result,minimum_later_delay_seconds=300)
    assert out['passed'] and out['gate']['source_disjoint_transfers']==3 and not registry.exists()
    stored=json.loads(state.read_text())
    for row in stored['episodes']: row['later_challenge']['not_before_epoch']=0
    state.write_text(json.dumps(stored)); closed=m.close_later_challenges(atom_registry_path=atoms,state_path=state,result_path=result)
    assert closed['gate']['later_retention_credits']==4
    runtime=m.GovernedMeasurementRuntime(registry); cases=m._cases([1,2,3,4,5,6])
    assert runtime.execute(m.MEASUREMENT_ID,cases['transient'])['classification']=='TRANSIENT_EVIDENCE_DEFECT'

def test_measurement_security_and_ood()->None:
    assert all(row['rejected'] for row in m._security_properties()); spec,_=m.invent_measurement()
    assert m.execute_measurement(spec,m._cases([1,2,3,4,5,6])['mixed'])['classification']=='ABSTAIN'
