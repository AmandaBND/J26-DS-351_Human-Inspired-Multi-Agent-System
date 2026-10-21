"""Human-reviewed segment roles; independent of diarization and emotion models."""
from math import isfinite

ROLES = ('Unassigned', 'Agent', 'Customer', 'Exclude')
REVIEW_KEYS = ('raw_speaker_turns', 'speaker_review_duration', 'speaker_review_epoch',
               'speaker_review_draft', 'confirmed_role_signature', 'review_bulk_agent',
               'review_split_segment', 'review_split_time')


def invalidate_review(state):
    state['role_review_confirmed'] = False
    for key in ('verified_speaker_turns', 'analysis_results', 'confirmed_role_signature'):
        state.pop(key, None)


def clear_segment_review(state):
    for key in list(state):
        if key in REVIEW_KEYS or str(key).startswith('segment_role_editor_'):
            state.pop(key, None)


def signature(rows):
    return tuple((r.get('Start (s)'), r.get('End (s)'), r.get('Detected Speaker'),
                  r.get('Verified Role')) for r in rows)


def validate_review(rows, duration):
    """Require explicit decisions and disjoint, finite intervals within the recording."""
    if not isfinite(duration) or duration <= 0:
        raise ValueError('Recording duration must be positive.')
    validated = []
    for index, row in enumerate(rows, 1):
        try:
            start, end = float(row['Start (s)']), float(row['End (s)'])
        except (ValueError, TypeError, KeyError):
            raise ValueError(f'Segment {index}: enter valid start and end times.') from None
        if not (isfinite(start) and isfinite(end) and 0 <= start < end <= duration):
            raise ValueError(f'Segment {index}: times must be within the recording, with end after start.')
        role = row.get('Verified Role')
        if role not in ROLES[1:]:
            raise ValueError(f'Segment {index}: select Agent, Customer or Exclude.')
        speaker = row.get('Detected Speaker')
        if not speaker:
            raise ValueError(f'Segment {index}: missing detected speaker evidence.')
        validated.append(dict(row, **{'Start (s)': start, 'End (s)': end}))
    validated.sort(key=lambda r: r['Start (s)'])
    for previous, current in zip(validated, validated[1:]):
        if current['Start (s)'] < previous['End (s)']:
            raise ValueError('Segments overlap. Adjust their boundaries before confirming.')
    if not any(r['Verified Role'] == 'Customer' for r in validated):
        raise ValueError('Mark at least one segment as Customer before analyzing.')
    return validated


def sync_review(state, rows):
    state['speaker_review_draft'] = [dict(r) for r in rows]
    if signature(rows) != state.get('confirmed_role_signature'):
        invalidate_review(state)


def confirm_review(state, rows, duration):
    invalidate_review(state)
    validated = validate_review(rows, duration)
    state['verified_speaker_turns'] = validated
    state['confirmed_role_signature'] = signature(rows)
    state['role_review_confirmed'] = True
    return validated


def apply_bulk_roles(rows, agent):
    speakers = {r['Detected Speaker'] for r in rows}
    if len(speakers) != 2 or agent not in speakers:
        raise ValueError('Bulk assignment requires exactly two detected speakers.')
    return [dict(r, **{'Verified Role': 'Agent' if r['Detected Speaker']==agent else 'Customer'}) for r in rows]


def split_segment(rows, index, at):
    row = rows[index]
    at = float(at)
    if not row['Start (s)'] < at < row['End (s)']:
        raise ValueError('Split time must fall inside the selected segment.')
    return [dict(r) for r in rows[:index]] + [
        dict(row, **{'End (s)': at}), dict(row, **{'Start (s)': at})
    ] + [dict(r) for r in rows[index+1:]]


def render_speaker_role_review(st):
    """Editable review with immutable raw evidence stored separately in session state."""
    state = st.session_state
    st.subheader('Review Speaker Roles')
    rows = state['speaker_review_turns']
    speakers = list(dict.fromkeys(r['Detected Speaker'] for r in rows))
    st.caption('Listen to the segments below. Correct roles or timing in the table, then confirm. Exclude silence or speech you cannot assign.')
    if len(speakers) == 2:
        agent = st.selectbox('Select the Service Agent', [None]+speakers,
            format_func=lambda s: 'Choose after listening' if s is None else str(s), key='review_bulk_agent')
        if st.button('Apply roles to all segments', disabled=agent is None):
            state['speaker_review_turns'] = apply_bulk_roles(state.get('speaker_review_draft', rows), agent)
            invalidate_review(state)
            state['speaker_review_epoch'] = state.get('speaker_review_epoch', 0)+1
            st.rerun()
    editor = st.data_editor(rows, hide_index=True, use_container_width=True,
        num_rows='fixed', disabled=['Detected Speaker'],
        column_config={
            'Start (s)': st.column_config.NumberColumn('Start (s)', min_value=0.0, step=0.01, required=True, format='%.3f'),
            'End (s)': st.column_config.NumberColumn('End (s)', min_value=0.0, step=0.01, required=True, format='%.3f'),
            'Verified Role': st.column_config.SelectboxColumn('Verified Role', options=ROLES, required=True)},
        key=f"segment_role_editor_{state.get('speaker_review_epoch', 0)}",
        on_change=invalidate_review, args=(state,))
    edited = editor.to_dict('records') if hasattr(editor, 'to_dict') else [dict(r) for r in editor]
    sync_review(state, edited)
    with st.expander('Split a segment containing both speakers'):
        index = st.selectbox('Segment to split', range(len(edited)),
            format_func=lambda i: f"Segment {i+1}: {edited[i]['Start (s)']}â€“{edited[i]['End (s)']}s", key='review_split_segment')
        at = st.number_input('Split at (seconds)', min_value=0.0, step=0.01, key='review_split_time')
        if st.button('Split segment'):
            try:
                state['speaker_review_turns'] = split_segment(edited, index, at)
                invalidate_review(state)
                state['speaker_review_epoch'] = state.get('speaker_review_epoch', 0)+1
                st.rerun()
            except (ValueError, TypeError) as exc:
                st.error(str(exc))
    if st.button('Confirm Speaker Roles', type='primary', key='confirm_speaker_roles'):
        try:
            confirm_review(state, edited, state['speaker_review_duration'])
        except ValueError as exc:
            st.error(str(exc))
    with st.expander('Speaker identification evidence'):
        st.json({'raw_diarization': state.get('raw_speaker_turns', ())})
    if state.get('role_review_confirmed'):
        st.success('Speaker roles confirmed. Customer-only analysis is ready.')
