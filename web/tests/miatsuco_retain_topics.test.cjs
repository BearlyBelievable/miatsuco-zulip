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

run_test("retain_topics event updates the channel and its setting element", () => {
    stream_data.clear_subscriptions();
    const sub = make_stream({
        subscribed: true,
        name: "dev help",
        stream_id: 2,
    });
    stream_data.add_sub_for_tests(sub);
    assert.equal(sub.miatsuco_retain_topics, false);

    const stub = make_stub();
    stream_ui_updates.update_setting_element = stub.f;
    stream_events.update_property(sub.stream_id, "miatsuco_retain_topics", true);

    assert.equal(sub.miatsuco_retain_topics, true);
    assert.equal(stub.num_calls, 1);
    const args = stub.get_args("sub", "setting_name");
    assert.equal(args.sub.stream_id, sub.stream_id);
    assert.equal(args.setting_name, "miatsuco_retain_topics");
});
