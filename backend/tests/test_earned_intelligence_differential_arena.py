from pathlib import Path
from backend.modules.hexcore.earned_intelligence_differential_arena import run

def test_answer_book_loses_delayed_advantage_while_retained_methods_transfer(tmp_path:Path):
 for relative in [
  'results/hexcore_cross_domain_method_transfer.json','results/hexcore_cross_domain_semantic_transfer.json',
  'results/hexcore_rust_sql_construction_and_selection.json','results/hexcore_open_causal_scientific_learning.json','results/hexcore_open_useful_objectives.json']:
  p=tmp_path/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
 result=run(repo_root=tmp_path,result_path=tmp_path/'result.json',state_path=tmp_path/'learning.json')
 assert result['passed'] is True
 assert result['gate']['warm_delayed_success']==6
 assert result['gate']['answerbook_delayed_success']==0
 assert result['gate']['positive_differentials']==6
