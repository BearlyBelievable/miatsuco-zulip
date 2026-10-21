"use strict";

const assert = require("node:assert/strict");

const {make_realm} = require("./lib/example_realm.cjs");
const {make_stream} = require("./lib/example_stream.cjs");
const {make_cross_realm_bot, make_user} = require("./lib/example_user.cjs");
const {$t} = require("./lib/i18n.cjs");
const {mock_esm, zrequire} = require("./lib/namespace.cjs");
const {run_test} = require("./lib/test.cjs");
const $ = require("./lib/zjquery.cjs");

const channel = mock_esm("../src/channel");
const confirm_dialog = mock_esm("../src/confirm_dialog");
const dialog_widget = mock_esm("../src/dialog_widget");
mock_esm("../src/timerender", {absolute_time: () => "Oct 1, 2026"});

const email_addresses = zrequire("miatsuco_channel_email_addresses");
const people = zrequire("people");
const {set_current_user, set_realm} = zrequire("state_data");
const sub_store = zrequire("sub_store");

set_realm(make_realm());
set_current_user({user_id: 1});

const me = make_user({email: "me@example.com", user_id: 1, full_name: "Me"});
const bob = make_user({email: "bob@example.com", user_id: 3, full_name: "Bob"});
const gateway_bot = make_cross_realm_bot({
    email: "emailgateway@example.com",
    user_id: 2,
    full_name: "Email Gateway",
});

people.init();
people.add_active_user(me);
people.add_active_user(bob);
people.add_cross_realm_user(gateway_bot);
people.initialize_current_user(me.user_id);

const sub = make_stream({stream_id: 10, name: "Denmark", subscribed: true});
sub_store.add_hydrated_sub(sub.stream_id, sub);

const SETTINGS_SELECTOR = `#subscription_overlay .subscription_settings[data-stream-id='${CSS.escape("10")}']`;
const LIST_TEMPLATE = "stream_settings/miatsuco_channel_email_addresses.hbs";

function capture_get() {
    const requests = [];
    channel.get = (opts) => {
        requests.push(opts);
    };
    return requests;
}

function setup_list() {
    const $list = $.create("email addresses list");
    $(SETTINGS_SELECTOR).set_find_results(".miatsuco-email-addresses-list", $list);
    return $list;
}

run_test("refresh lists the generated addresses", ({mock_template}) => {
    const $list = setup_list();
    const requests = capture_get();
    let list_data;
    mock_template(LIST_TEMPLATE, false, (data) => {
        list_data = data;
        return "<list>";
    });

    email_addresses.refresh(sub);
    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, "/json/streams/10/email_addresses");

    requests[0].success({
        email_addresses: [
            {
                id: 1,
                email: "denmark.token@example.com",
                creator_id: me.user_id,
                sender_id: gateway_bot.user_id,
                date_created: 1000,
            },
            {
                id: 2,
                email: null,
                creator_id: bob.user_id,
                sender_id: bob.user_id,
                date_created: 2000,
            },
            {id: 3, email: null, creator_id: null, sender_id: 99, date_created: 3000},
        ],
    });

    assert.equal($list.html(), "<list>");
    assert.deepEqual(list_data, {
        has_addresses: true,
        email_addresses: [
            {
                id: 1,
                address: "denmark.token@example.com",
                sender_name: $t({defaultMessage: "Email Gateway bot"}),
                creator_name: "Me",
                created_date: "Oct 1, 2026",
            },
            {
                id: 2,
                address: "",
                sender_name: "Bob",
                creator_name: "Bob",
                created_date: "Oct 1, 2026",
            },
            {
                id: 3,
                address: "",
                sender_name: $t({defaultMessage: "Unknown user"}),
                creator_name: $t({defaultMessage: "Unknown user"}),
                created_date: "Oct 1, 2026",
            },
        ],
    });
});

run_test("revoke button confirms and deletes the address", () => {
    email_addresses.initialize();
    const handler = $("#channels_overlay_container").get_on_handler(
        "click",
        ".miatsuco-revoke-email-address",
    );
    const $button = $(".miatsuco-revoke-email-address");
    const $panel = $(SETTINGS_SELECTOR);
    $panel.attr("data-stream-id", "10");
    $button.set_closest_results(".subscription_settings", $panel);
    const $card = $.create("address card");
    $card.attr("data-email-address-id", "7");
    $button.set_closest_results("[data-email-address-id]", $card);
    setup_list();

    let dialog;
    confirm_dialog.launch = (conf) => {
        dialog = conf;
    };
    let prevented = false;
    let stopped = false;
    handler.call(".miatsuco-revoke-email-address", {
        preventDefault() {
            prevented = true;
        },
        stopPropagation() {
            stopped = true;
        },
    });
    assert.ok(prevented && stopped);
    assert.equal(dialog.modal_submit_button_text, $t({defaultMessage: "Revoke"}));

    const requests = capture_get();
    let request_args;
    dialog_widget.submit_api_request = (...args) => {
        request_args = args;
    };
    dialog.on_click();
    assert.equal(dialog.loading_spinner, true);
    const [request_method, url, data, opts] = request_args;
    assert.equal(request_method, channel.del);
    assert.equal(url, "/json/streams/10/email_addresses/7");
    assert.deepEqual(data, {});

    opts.success_continuation();
    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, "/json/streams/10/email_addresses");
});
