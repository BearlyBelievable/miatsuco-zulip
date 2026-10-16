"use strict";

const assert = require("node:assert/strict");

const {make_realm} = require("./lib/example_realm.cjs");
const {mock_esm, zrequire} = require("./lib/namespace.cjs");
const {run_test} = require("./lib/test.cjs");

const stream_data = mock_esm("../src/stream_data");

const message_edit = zrequire("message_edit");
const {set_current_user, set_realm} = zrequire("state_data");

const realm = make_realm();
set_realm(realm);
const current_user = {};
set_current_user(current_user);

run_test("topic and stream edits in a pinned topic", ({override}) => {
    override(realm, "realm_allow_message_editing", true);
    override(stream_data, "is_stream_archived_by_id", () => false);
    override(stream_data, "user_can_move_messages_within_channel", () => true);
    override(stream_data, "user_can_move_messages_out_of_channel", () => true);
    override(stream_data, "is_empty_topic_only_channel", () => false);
    override(stream_data, "get_sub_by_id", () => ({stream_id: 7}));
    override(current_user, "is_moderator", true);
    let can_administer = false;
    override(stream_data, "can_administer_channel", () => can_administer);

    const message = {
        sent_by_me: true,
        type: "stream",
        stream_id: 7,
        topic: "📌 plans",
    };
    assert.equal(message_edit.is_topic_editable(message), false);
    assert.equal(message_edit.is_stream_editable(message), false);

    can_administer = true;
    assert.equal(message_edit.is_topic_editable(message), true);
    assert.equal(message_edit.is_stream_editable(message), false);

    can_administer = false;
    message.topic = "plans";
    assert.equal(message_edit.is_topic_editable(message), true);
    assert.equal(message_edit.is_stream_editable(message), true);
});
