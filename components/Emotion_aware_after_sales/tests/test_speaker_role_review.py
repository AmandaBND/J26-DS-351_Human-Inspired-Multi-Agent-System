"""Segment corrections must control the samples sent to customer emotion analysis."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from emotion_aware_after_sales.services.speaker_role_review_service import (
    apply_bulk_roles, clear_segment_review, confirm_review, signature,
    split_segment, sync_review, validate_review,
)
from emotion_aware_after_sales.services.customer_audio_service import CustomerAudioService
from emotion_aware_after_sales.services.diarization_service import SpeakerTurn
from emotion_aware_after_sales.services.voice_customer_service import reset_customer_context

def rows():
    return [
        {'Start (s)':0.,'End (s)':1.,'Detected Speaker':'S0','Verified Role':'Customer'},
        {'Start (s)':1.,'End (s)':2.,'Detected Speaker':'S0','Verified Role':'Agent'},
        {'Start (s)':2.,'End (s)':3.,'Detected Speaker':'S1','Verified Role':'Exclude'},
    ]

def test_individual_roles_override_same_detected_speaker_in_real_analysis_path():
    state={}
    corrected=confirm_review(state,rows(),3.)
    # Execute the app's analysis function without loading its unrelated model/UI imports.
    source=Path(__file__).parents[1]/'app.py'
    tree=ast.parse(source.read_text(encoding='utf-8-sig'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_cached_acoustic_analysis')
    function.decorator_list=[]
    calls=[]
    class ExistingModelSpy:
        def analyze(self,segments):
            calls.append(segments)
            return ['existing model output']
    audio=SimpleNamespace(samples=np.arange(30,dtype=np.float32),sample_rate=10)
    env=dict(preprocess_bytes=lambda *_:audio,SpeakerTurn=SpeakerTurn,CustomerAudioService=CustomerAudioService,
             TemporalAcousticService=ExistingModelSpy,EmotionAcousticFeaturesService=ExistingModelSpy,
             EGeMAPSSERService=ExistingModelSpy)
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),env)
    output=env['run_cached_acoustic_analysis'](b'audio','test.wav',signature(corrected))
    assert len(calls)==3
    for segments in calls:
        assert len(segments)==1
        np.testing.assert_array_equal(segments[0].samples,audio.samples[:10])
    assert output[-1]==['existing model output']

@pytest.mark.parametrize('field,value',[('Verified Role','Agent'),('Start (s)',0.1),('End (s)',0.9)])
def test_every_edit_invalidates_confirmed_roles_and_stale_emotions(field,value):
    state={'role_scores':{'explanation':'keep evidence'},'raw_speaker_turns':((0,1,'S0'),)}
    original=deepcopy(state)
    confirm_review(state,rows(),3.)
    state['analysis_results']={'emotion':'stale'}
    edited=rows();edited[0][field]=value
    sync_review(state,edited)
    assert not state['role_review_confirmed']
    assert 'analysis_results' not in state
    assert 'verified_speaker_turns' not in state
    assert state['role_scores']==original['role_scores']
    assert state['raw_speaker_turns']==original['raw_speaker_turns']

def test_unchanged_review_keeps_confirmation():
    state={};confirm_review(state,rows(),3.)
    state['analysis_results']={'emotion':'valid'}
    sync_review(state,rows())
    assert state['role_review_confirmed']
    assert state['analysis_results']=={'emotion':'valid'}

@pytest.mark.parametrize('start,end,role',[
    (-1,1,'Customer'),(0,4,'Customer'),(1,1,'Customer'),
    (float('nan'),1,'Customer'),(0,float('inf'),'Customer'),
    (0,1,'Unassigned'),(0,1,'Invalid'),(0,1,None),
])
def test_invalid_drafts_never_enable_analysis(start,end,role):
    draft=rows();draft[0].update({'Start (s)':start,'End (s)':end,'Verified Role':role})
    state={};confirm_review(state,rows(),3.)
    with pytest.raises(ValueError): confirm_review(state,draft,3.)
    assert not state['role_review_confirmed']
    assert 'verified_speaker_turns' not in state

def test_overlap_and_no_customer_rejected():
    draft=rows();draft[1]['Start (s)']=.5
    with pytest.raises(ValueError,match='overlap'): validate_review(draft,3.)
    with pytest.raises(ValueError,match='at least one'): validate_review(apply_bulk_roles(rows(),'S0')[:2],3.)

def test_customer_can_speak_first_and_split_corrects_merged_turn_without_changing_evidence():
    raw=rows();before=deepcopy(raw)
    draft=apply_bulk_roles(raw,'S1')
    assert draft[0]['Verified Role']=='Customer'
    split=split_segment(draft,0,.4)
    split[1]['Verified Role']='Agent'
    verified=validate_review(split,3.)
    assert verified[0]['Verified Role']=='Customer'
    assert verified[1]['Verified Role']=='Agent'
    assert raw==before
    with pytest.raises(ValueError): split_segment(raw,0,1.)

def test_one_speaker_can_be_corrected_per_segment_and_context_change_clears_editor():
    draft=rows()[:2]
    assert len({r['Detected Speaker'] for r in validate_review(draft,2.)})==1
    state={'voice_customer_context':(1,1),'speaker_review_draft':draft,
           'segment_role_editor_7':{'edited_rows':{}},'raw_speaker_turns':((0,2,'S0'),)}
    reset_customer_context(state,(2,2))
    assert state=={'voice_customer_context':(2,2)}

@pytest.mark.parametrize('turns,expected', [
    ([(1.,2.,'S1'),(0.,1.,'S0')], {'S0':'Agent','S1':'Customer'}),
    ([(0.,1.,'S0'),(1.,2.,'S0')], {'S0':'Agent'}),
    ([(0.,1.,'S0'),(1.,2.,'S1'),(2.,3.,'S2')],
     {'S0':'Agent','S1':'Customer','S2':'Unassigned'}),
])
def test_detection_suggests_amc_prior_in_temporal_order(turns, expected):
    source=Path(__file__).parents[1]/'app.py'
    tree=ast.parse(source.read_text(encoding='utf-8-sig'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_cached_role_identification')
    function.decorator_list=[]
    env={'run_cached_diarization':lambda *_:turns}
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),env)
    mapping,evidence,_=env['run_cached_role_identification'](b'audio','test.wav')
    assert mapping==expected
    assert evidence['customer_speaker']==('S1' if len(expected)>1 else None)
    assert evidence['method']=='first_speaker_amc_prior'
    assert evidence['requires_review']
