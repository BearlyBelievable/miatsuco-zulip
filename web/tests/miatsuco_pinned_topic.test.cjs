"use strict";

const assert = require("node:assert/strict");

const {mock_esm, zrequire} = require("./lib/namespace.cjs");
const {run_test} = require("./lib/test.cjs");

const buttons = mock_esm("../src/buttons");
const channel = mock_esm("../src/channel");
const ui_report = mock_esm("../src/ui_report");

const miatsuco_pinned_topic = zrequire("miatsuco_pinned_topic");

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
    let hid_indicator = false;
    override(buttons, "show_button_loading_indicator", () => {});
    override(buttons, "hide_button_loading_indicator", () => {
        hid_indicator = true;
    });

    const $row = {find: () => ({})};
    miatsuco_pinned_topic.toggle_pinned_topic(10, "plans", $row);
    request.error({responseJSON: {msg: "Only channel administrators can pin."}});
    assert.deepEqual(reported, ["Only channel administrators can pin."]);
    assert.ok(hid_indicator);
});
