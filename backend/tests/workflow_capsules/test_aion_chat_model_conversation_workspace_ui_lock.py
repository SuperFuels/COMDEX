from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_chat_history_is_grouped_and_persisted_per_model():
    assert 'localStorage.getItem("aion.chat.sessions.v3")' in APP
    assert "ensureAionChatModelWorkspaceV3" in APP
    assert "getAionChatSessionsV3" in APP
    assert "active_chat_id" in APP


def test_existing_single_streams_are_migrated_without_being_discarded():
    assert "getAionChatMessageStreamsV2()" in APP
    assert "legacyMessages" in APP
    assert "createAionChatSessionRecordV3(legacyMessages)" in APP


def test_sidebar_can_create_open_and_delete_model_conversations():
    assert "createAionChatSessionV3(engine)" in APP
    assert 'data-aion-chat-select-session="${escapeHtml(chat.id)}"' in APP
    assert 'data-aion-chat-delete-session="${escapeHtml(chat.id)}"' in APP
    assert "deleteAionChatSessionV3(engine, sessionId)" in APP
    assert "This removes this chat history from this Mac and cannot be undone." in APP


def test_every_model_keeps_one_ready_new_chat_entry():
    assert "const hasReadyNewChat" in APP
    assert "if (!hasReadyNewChat)" in APP
    assert "const readyChat = workspace.chats.find" in APP
    assert 'String(chat.title || "") === "New chat"' in APP
    assert "safeArray(chat.messages).length === 0" in APP


def test_async_responses_remain_attached_to_the_originating_chat():
    assert "const chatSessionId = getAionChatActiveSessionIdV3(engine);" in APP
    assert "getAionChatMessagesV1(engine, chatSessionId)" in APP
    assert "setAionChatMessagesV1([...priorMessages, userMessage], engine, chatSessionId)" in APP


def test_render_signature_includes_chat_list_and_active_chat():
    assert "sessions," in APP
    assert "activeSessionId," in APP
    assert "message_count: safeArray(chat?.messages).length" in APP


def test_chat_sidebar_uses_brand_hover_colours_not_legacy_cream():
    assert ".aion-chat-new-v1:hover" in APP
    assert "background:#e8f1ff!important" in APP
    assert ".aion-chat-thread-delete-v1:hover" in APP
    assert "background:#dce9ff!important" in APP
    assert "border:0!important" in APP
