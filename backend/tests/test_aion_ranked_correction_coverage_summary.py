from backend.scripts.run_aion_ranked_correction_local_gate import coverage_summary


def test_unmatched_calls_remain_in_denominator():
    development=[{'rank':4} for _ in range(4)]
    results=[{'rank':4,'status':'LOCAL_CANDIDATE_REQUIRES_UNTOUCHED_VALIDATION',
              'observations':[{'supported':True,'local_pass':True},
                              {'supported':False}]}]
    result=coverage_summary(development,results)['4']
    assert result['all_development_calls']==4
    assert result['calls_without_fitted_identity']==2
    assert result['candidate_traffic_share']==.25
    assert result['certified_traffic_share'] is None


def test_failed_region_not_counted_as_usable():
    results=[{'rank':2,'status':'NOT_CERTIFIED','observations':[
        {'supported':True,'local_pass':True},
        {'supported':True,'local_pass':False}]}]
    summary=coverage_summary([{'rank':2},{'rank':2}],results)
    assert summary['2']['local_passing_calls']==1
    assert summary['2']['candidate_traffic_share']==0
    assert summary['3']['candidate_traffic_share'] is None
