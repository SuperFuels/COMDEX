# Minimal CRDTRegistry definition for singleton
class CRDTRegistry:
    def __init__(self):
        self.locks = {}

    def acquire_lock(self, glyph_id, agent_id):
        if glyph_id not in self.locks:
            self.locks[glyph_id] = agent_id
            return True
        return False

    def release_lock(self, glyph_id, agent_id):
        if self.locks.get(glyph_id) == agent_id:
            del self.locks[glyph_id]
            return True
        return False

    def get_current_locks(self):
        return self.locks.copy()