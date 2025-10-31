import hashlib, json

def entropy_signature(env):
    payload = json.dumps(sorted(env.keys()), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]

def verify_lock(expected, env):
    return expected == entropy_signature(env)