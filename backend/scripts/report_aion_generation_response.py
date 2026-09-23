"""Offline response inspection; requires free inference lease before SD metadata."""
import argparse
import fcntl
import json
from pathlib import Path

from backend.modules.aion_inference.gptoss_gguf_tokenizer import GptOssGGUFTokenizer
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('refusing to overwrite response evidence')
    receipt = json.loads(args.receipt.read_text())
    body = dict(receipt)
    if body.pop('canonical_sha256') != canonical(body):
        raise SystemExit('receipt hash mismatch')
    with Path('.runtime/aion-gptoss-inference.lock').open('a') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        tokenizer = GptOssGGUFTokenizer.from_warehouse(args.manifest)
    reports = []
    prompt_count = receipt.get('prompt_token_count', len(receipt.get('input_token_ids', [])))
    if not isinstance(prompt_count, int) or prompt_count < 1:
        raise SystemExit('receipt lacks a valid prompt-token count')
    for label in ('run_a', 'run_b'):
        # Last prefill evaluation predicts the FIRST response token.
        rows = [row for row in receipt[label]['tokens']
                if row['position'] >= prompt_count - 1]
        ids = [row['generated_token_id'] for row in rows]
        # GPT-OSS Harmony uses end/return markers; older FIM-only logic would
        # silently miss a finished assistant turn.
        markers = {name: tokenizer.special[name] for name in
                   ('<|end|>', '<|return|>', '<|endoftext|>')
                   if name in tokenizer.special}
        located = [(ids.index(value), name) for name, value in markers.items()
                   if value in ids]
        first_end, marker_name = min(located) if located else (None, None)
        bounded = ids if first_end is None else ids[:first_end+1]
        reports.append(dict(pass_label=label, response_start_evaluation_position=prompt_count-1,
            generated_ids_including_after_end=ids, first_turn_marker=marker_name,
            first_assistant_turn_end_index=first_end,
            response_text_through_first_turn_end=tokenizer.decode(bounded),
            tokens_after_first_turn_end=0 if first_end is None else len(ids)-first_end-1,
            completed_turn_marker_observed=first_end is not None))
    body = dict(receipt_sha256=digest(args.receipt), manifest_sha256=digest(args.manifest),
                reports=reports, claim_boundary='Decoded observation only, no automatic factual '
                'or semantic quality pass. Fixed-length benchmark tokens after a turn-end marker '
                'must not be called additional completed-answer throughput.')
    body['canonical_sha256'] = canonical(body)
    with args.output.open('x') as handle:
        json.dump(body, handle, indent=2, sort_keys=True)
    print(json.dumps(body), flush=True)


if __name__ == '__main__':
    main()
