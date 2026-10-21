"use strict";

const assert = require("node:assert/strict");

const {make_realm} = require("./lib/example_realm.cjs");
const {make_stream} = require("./lib/example_stream.cjs");
const {mock_esm, zrequire} = require("./lib/namespace.cjs");
const {make_stub} = require("./lib/stub.cjs");
const {run_test} = require("./lib/test.cjs");

const stream_ui_updates = mock_esm("../src/stream_ui_updates");

const stream_data = zrequire("stream_data");
const stream_events = zrequire("stream_events");
const {set_current_user, set_realm} = zrequire("state_data");

set_current_user({});
set_realm(make_realm());

run_test("user email posting event updates the channel, its setting, and the email section", () => {
    stream_data.clear_subscriptions();
    const sub = make_stream({
        subscribed: true,
        name: "dev help",
        stream_id: 2,
    });
    stream_data.add_sub_for_tests(sub);
    assert.equal(sub.miatsuco_allow_user_email_posting, false);

    const setting_stub = make_stub();
    stream_ui_updates.update_setting_element = setting_stub.f;
    const email_section_stub = make_stub();
    stream_ui_updates.update_channel_email_section = email_section_stub.f;
    stream_events.update_property(sub.stream_id, "miatsuco_allow_user_email_posting", true);

    assert.equal(sub.miatsuco_allow_user_email_posting, true);
    assert.equal(setting_stub.num_calls, 1);
    const args = setting_stub.get_args("sub", "setting_name");
    assert.equal(args.sub.stream_id, sub.stream_id);
    assert.equal(args.setting_name, "miatsuco_allow_user_email_posting");
    assert.equal(email_section_stub.num_calls, 1);
});

run_test("email posting event updates the channel, its setting, and the email section", () => {
    stream_data.clear_subscriptions();
    const sub = make_stream({
        subscribed: true,
        name: "dev help",
        stream_id: 2,
    });
    stream_data.add_sub_for_tests(sub);
    assert.equal(sub.miatsuco_allow_email_posting, false);

    const setting_stub = make_stub();
    stream_ui_updates.update_setting_element = setting_stub.f;
    const email_section_stub = make_stub();
    stream_ui_updates.update_channel_email_section = email_section_stub.f;
    stream_events.update_property(sub.stream_id, "miatsuco_allow_email_posting", true);

    assert.equal(sub.miatsuco_allow_email_posting, true);
    assert.equal(setting_stub.num_calls, 1);
    const args = setting_stub.get_args("sub", "setting_name");
    assert.equal(args.sub.stream_id, sub.stream_id);
    assert.equal(args.setting_name, "miatsuco_allow_email_posting");
    assert.equal(email_section_stub.num_calls, 1);
});
