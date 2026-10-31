"use strict";

const assert = require("node:assert/strict");

const {make_realm} = require("./lib/example_realm.cjs");
const {$t} = require("./lib/i18n.cjs");
const {mock_esm, zrequire} = require("./lib/namespace.cjs");
const {run_test, noop} = require("./lib/test.cjs");

const buttons = mock_esm("../src/buttons");
const channel = mock_esm("../src/channel");
const ui_report = mock_esm("../src/ui_report");

const miatsuco_pinned_topic = zrequire("miatsuco_pinned_topic");
const stream_topic_history = zrequire("stream_topic_history");
const {set_realm} = zrequire("state_data");

run_test("resolve_topic_name", () => {
    stream_topic_history.reset();
    stream_topic_history.set_update_topic_last_message_id(noop);
    for (const [message_id, topic_name] of [
        [1, "📌 plans"],
        [2, "chores"],
    ]) {
        stream_topic_history.add_message({stream_id: 1, topic_name, message_id});
    }

    assert.equal(miatsuco_pinned_topic.resolve_topic_name(1, "plans"), "📌 plans");
    assert.equal(miatsuco_pinned_topic.resolve_topic_name(1, "Plans"), "📌 Plans");
    assert.equal(miatsuco_pinned_topic.resolve_topic_name(1, "📌 plans"), "📌 plans");
    assert.equal(miatsuco_pinned_topic.resolve_topic_name(1, "📌 chores"), "chores");
    assert.equal(miatsuco_pinned_topic.resolve_topic_name(1, "chores"), "chores");
    assert.equal(miatsuco_pinned_topic.resolve_topic_name(1, "agenda"), "agenda");
});

run_test("is_local_echo_safe", () => {
    set_realm(make_realm({max_topic_length: 60}));
    stream_topic_history.reset();
    stream_topic_history.set_update_topic_last_message_id(noop);
    stream_topic_history.add_message({stream_id: 1, topic_name: "📌 plans", message_id: 1});

    assert.ok(miatsuco_pinned_topic.is_local_echo_safe(1, "📌 plans"));
    assert.ok(miatsuco_pinned_topic.is_local_echo_safe(1, "📌 PLANS"));
    assert.ok(!miatsuco_pinned_topic.is_local_echo_safe(1, "agenda"));

    stream_topic_history.mark_history_fetched_for(1);
    assert.ok(miatsuco_pinned_topic.is_local_echo_safe(1, "agenda"));
    assert.ok(miatsuco_pinned_topic.is_local_echo_safe(1, "a".repeat(57)));
    assert.ok(!miatsuco_pinned_topic.is_local_echo_safe(1, "a".repeat(58)));
});

run_test("topic names", () => {
    assert.ok(miatsuco_pinned_topic.is_pinned("📌 plans"));
    assert.ok(!miatsuco_pinned_topic.is_pinned("plans"));
    assert.ok(!miatsuco_pinned_topic.is_pinned("✔ 📌 plans"));

    assert.ok(miatsuco_pinned_topic.topic_pin_toggled("📌 plans", "plans"));
    assert.ok(miatsuco_pinned_topic.topic_pin_toggled("plans", "📌 plans"));
    assert.ok(!miatsuco_pinned_topic.topic_pin_toggled("plans", "📌 📌 plans"));
    assert.ok(miatsuco_pinned_topic.topic_pin_toggled("📌launch", "📌 📌launch"));
    assert.ok(!miatsuco_pinned_topic.topic_pin_toggled("📌 new plans", "📌 plans"));
    assert.ok(!miatsuco_pinned_topic.topic_pin_toggled("chores", "plans"));
});

run_test("sidebar ordering", () => {
    assert.deepEqual(miatsuco_pinned_topic.display_parts("📌 plans"), ["📌 ", "plans"]);
    assert.deepEqual(miatsuco_pinned_topic.display_parts("plans"), ["", "plans"]);
    assert.deepEqual(miatsuco_pinned_topic.pinned_first(["a", "b", "📌 c", "d", "📌 e"]), [
        "📌 c",
        "📌 e",
        "a",
        "b",
        "d",
    ]);
});

run_test("toggle_pinned_topic", ({override}) => {
    let request;
    override(channel, "patch", (opts) => {
        request = opts;
    });

    miatsuco_pinned_topic.toggle_pinned_topic(10, "plans");
    assert.equal(request.url, "/json/messages/10");
    assert.deepEqual(request.data, {
        propagate_mode: "change_all",
        topic: "📌 plans",
        send_notification_to_old_thread: false,
        send_notification_to_new_thread: false,
    });

    miatsuco_pinned_topic.toggle_pinned_topic(10, "📌 plans");
    assert.equal(request.data.topic, "plans");
});

run_test("toggle_pinned_topic errors", ({override}) => {
    let request;
    override(channel, "patch", (opts) => {
        request = opts;
    });
    const reported = [];
    override(ui_report, "generic_embed_error", (html) => {
        reported.push(html);
    });
    let base_message;
    override(channel, "xhr_error_message", (message, xhr) => {
        base_message = message;
        return `${message}: ${xhr.status}`;
    });
    let hid_indicator = false;
    override(buttons, "show_button_loading_indicator", () => {});
    override(buttons, "hide_button_loading_indicator", () => {
        hid_indicator = true;
    });

    const $row = {find: () => ({})};
    miatsuco_pinned_topic.toggle_pinned_topic(10, "plans", $row);
    request.error({status: 500});
    const failure = $t({defaultMessage: "Failed to pin or unpin the topic"});
    assert.equal(base_message, failure);
    assert.deepEqual(reported, [`${failure}: 500`]);
    assert.ok(hid_indicator);
});
