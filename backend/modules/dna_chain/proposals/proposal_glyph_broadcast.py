proposal_id = "crispr-glyph-broadcast-001"
file = "backend/routes/glyph_mutate.py"
reason = "Add mutation marker + broadcast glyph updates on WebSocket"
replaced_code = \"\"\"container["cubes"][req.coord]["glyph"] = req.glyph\"\"\"
new_code = \"\"\"container["cubes"][req.coord]["glyph"] = req.glyph
container["cubes"][req.coord]["mutated"] = True

# Broadcast glyph update
await websocket_manager.broadcast({
    "type": "glyph_update",
    "coord": req.coord,
    "glyph": req.glyph
})\"\"\"
diff = \"\"\"
+container["cubes"][req.coord]["mutated"] = True
+
+# Broadcast glyph update
+await websocket_manager.broadcast({
+    "type": "glyph_update",
+    "coord": req.coord,
+    "glyph": req.glyph
+})
\"\"\"
approved = False
timestamp = "2025-07-09T12:53:49Z"
