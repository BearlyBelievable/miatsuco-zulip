"use strict";

const assert = require("node:assert/strict");

const {mock_esm, zrequire} = require("./lib/namespace.cjs");
const {run_test} = require("./lib/test.cjs");
const $ = require("./lib/zjquery.cjs");

const compose_reply = mock_esm("../src/compose_reply");
const message_lists = mock_esm("../src/message_lists");
const miatsuco_pinned_topic = mock_esm("../src/miatsuco_pinned_topic");
const rows = mock_esm("../src/rows");

const click_handlers = zrequire("miatsuco_click_handlers");

run_test("touch-controls click handler clears selection on outside click", () => {
    click_handlers.initialize();
    const handler = $("body").get_on_handler("click");

    const $selected = $(".selected_msg_for_touchscreen");
    $selected.addClass("selected_msg_for_touchscreen");

    const $outside = $(".outside-element");
    $outside.set_closest_results(".message_row", []);

    handler({target: ".outside-element"});

    assert.ok(!$selected.hasClass("selected_msg_for_touchscreen"));
});

run_test("touch-controls click handler leaves selection alone for a message row click", () => {
    click_handlers.initialize();
    const handler = $("body").get_on_handler("click");

    const $selected = $(".selected_msg_for_touchscreen");
    $selected.addClass("selected_msg_for_touchscreen");

    const $inside = $(".inside-element");
    $inside.set_closest_results(".message_row", $(".message_row"));

    handler({target: ".inside-element"});

    assert.ok($selected.hasClass("selected_msg_for_touchscreen"));
});

run_test("quote_message_button click handler quotes the clicked message", () => {
    click_handlers.initialize();
    const handler = $("body").get_on_handler("click", ".quote_message_button");

    const $button = $(".quote_message_button");
    $button.set_closest_results(".message_row", $(".message_row"));
    rows.id = () => 42;
    message_lists.current = {
        get_row: () => $(".message_row"),
    };

    let quote_opts;
    compose_reply.quote_messages = (opts) => {
        quote_opts = opts;
    };

    let stopped = false;
    handler.call(".quote_message_button", {
        stopPropagation() {
            stopped = true;
        },
    });

    assert.deepEqual(quote_opts, {trigger: "message controls", message_id: 42});
    assert.ok(stopped);
});

run_test("pin and unpin buttons toggle the pinned topic of the clicked recipient bar", () => {
    click_handlers.initialize();
    const handler = $("body").get_on_handler(
        "click",
        ".message_header .on_hover_topic_pin, .message_header .on_hover_topic_unpin",
    );

    const $recipient_row = $.create("recipient row");
    const $message_header = $.create("message header");
    $message_header.attr("data-topic-name", "plans");
    const $button = $(".on_hover_topic_pin");
    $button.set_closest_results(".recipient_row", $recipient_row);
    $button.set_closest_results(".message_header", $message_header);
    rows.id_for_recipient_row = ($row) => {
        assert.equal($row[0], $recipient_row[0]);
        return 42;
    };

    let toggled;
    miatsuco_pinned_topic.toggle_pinned_topic = (...args) => {
        toggled = args;
    };
    let stopped = false;
    handler({
        target: ".on_hover_topic_pin",
        stopPropagation() {
            stopped = true;
        },
    });

    assert.deepEqual(toggled.slice(0, 2), [42, "plans"]);
    assert.equal(toggled[2][0], $recipient_row[0]);
    assert.ok(stopped);
});
