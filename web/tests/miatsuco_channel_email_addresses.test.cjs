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
const stream_data = mock_esm("../src/stream_data");
const confirm_dialog = mock_esm("../src/confirm_dialog");
const dialog_widget = mock_esm("../src/dialog_widget");
const ui_report = mock_esm("../src/ui_report");
mock_esm("../src/timerender", {absolute_time: () => "Oct 1, 2026"});

const email_addresses = zrequire("miatsuco_channel_email_addresses");
const people = zrequire("people");
const {set_current_user, set_realm} = zrequire("state_data");
const sub_store = zrequire("sub_store");

set_realm(make_realm());
set_current_user({user_id: 1});

const me = make_user({email: "me@example.com", user_id: 1, full_name: "Me"});
const bob = make_user({email: "bob@example.com", user_id: 3, full_name: "Bob"});
const own_bot = make_user({
    email: "bot@example.com",
    user_id: 5,
    full_name: "Own bot",
    is_bot: true,
});
const gateway_bot = make_cross_realm_bot({
    email: "emailgateway@example.com",
    user_id: 2,
    full_name: "Email Gateway",
});

people.init();
people.add_active_user(me);
people.add_active_user(bob);
people.add_active_user(own_bot);
people.add_cross_realm_user(gateway_bot);
people.initialize_current_user(me.user_id);

const sub = make_stream({
    stream_id: 10,
    name: "Denmark",
    subscribed: true,
    miatsuco_allow_user_email_posting: true,
    miatsuco_allow_email_posting: true,
});
sub_store.add_hydrated_sub(sub.stream_id, sub);

const SETTINGS_SELECTOR = `#subscription_overlay .subscription_settings[data-stream-id='${CSS.escape("10")}']`;
const LIST_TEMPLATE = "stream_settings/miatsuco_channel_email_addresses.hbs";
const PERSONAL_TEMPLATE = "stream_settings/miatsuco_personal_channel_email.hbs";

function address(fields) {
    return {
        email: "denmark.token@example.com",
        creator_id: me.user_id,
        sender_id: me.user_id,
        is_personal: false,
        date_created: 1000,
        ...fields,
    };
}

function setup_settings_panel() {
    const $settings = $(SETTINGS_SELECTOR);
    const $box = $.create("email addresses box");
    const $list = $.create("email addresses list");
    const $personal = $.create("personal email content");
    $settings.set_find_results(".miatsuco-email-addresses-box", $box);
    $box.set_find_results(".miatsuco-email-addresses-list", $list);
    $settings.set_find_results(".miatsuco-personal-email-content", $personal);
    return {$settings, $box, $list, $personal};
}

function capture_get() {
    const requests = [];
    channel.get = (opts) => {
        requests.push(opts);
    };
    return requests;
}

run_test(
    "refresh renders every kind of address for an administrator",
    ({override, mock_template}) => {
        override(stream_data, "can_administer_channel", () => true);
        override(stream_data, "can_post_messages_in_stream", () => true);
        override(
            stream_data,
            "get_current_user_and_their_bots_with_post_messages_permission",
            () => [me, own_bot],
        );
        const {$box, $list, $personal} = setup_settings_panel();
        const requests = capture_get();

        let list_data;
        mock_template(LIST_TEMPLATE, false, (data) => {
            list_data = data;
            return "<list>";
        });
        let personal_data;
        mock_template(PERSONAL_TEMPLATE, false, (data) => {
            personal_data = data;
            return "<personal>";
        });

        email_addresses.refresh(sub);
        assert.equal(requests.length, 1);
        assert.equal(requests[0].url, "/json/streams/10/email_addresses");

        requests[0].success({
            email_addresses: [
                address({id: 1, sender_id: gateway_bot.user_id}),
                address({id: 2, creator_id: bob.user_id, sender_id: own_bot.user_id, email: null}),
                address({id: 3, sender_id: 99}),
                address({id: 4, is_personal: true}),
                address({
                    id: 5,
                    is_personal: true,
                    creator_id: bob.user_id,
                    sender_id: bob.user_id,
                }),
                address({id: 6, creator_id: null, sender_id: gateway_bot.user_id, email: null}),
            ],
        });

        assert.ok($box.visible());
        assert.equal($list.html(), "<list>");
        assert.equal($personal.html(), "<personal>");

        assert.equal(list_data.has_addresses, true);
        assert.equal(list_data.has_bot_addresses, true);
        assert.equal(list_data.has_personal_addresses, true);
        assert.deepEqual(
            list_data.slots.map((slot) => [slot.id ?? slot.sender_id, slot.sender_name]),
            [
                [3, $t({defaultMessage: "Unknown user"})],
                [1, $t({defaultMessage: "Email Gateway bot"})],
                [own_bot.user_id, "Own bot"],
            ],
        );
        assert.equal(list_data.slots[2].is_empty, true);
        assert.deepEqual(
            list_data.others.map((card) => [card.id, card.address, card.has_options]),
            [
                [2, "", false],
                [6, "", false],
            ],
        );
        assert.deepEqual(
            list_data.personal.map((card) => [card.id, card.address]),
            [
                [4, ""],
                [5, ""],
            ],
        );
        assert.equal(list_data.others[1].creator_name, $t({defaultMessage: "Unknown user"}));
        assert.equal(list_data.slots[1].has_options, true);
        assert.deepEqual(
            list_data.slots[1].tags.map((tag) => [tag.name, tag.checked]),
            [
                ["show-sender", true],
                ["include-footer", false],
                ["include-quotes", false],
                ["prefer-html", false],
            ],
        );

        assert.deepEqual(personal_data, {
            has_address: true,
            is_enabled: true,
            can_generate: true,
            address: "denmark.token@example.com",
            address_id: 4,
        });
    },
);

run_test(
    "refresh for a member who cannot post only hides the personal address",
    ({override, mock_template}) => {
        override(stream_data, "can_administer_channel", () => false);
        override(stream_data, "can_post_messages_in_stream", () => false);
        const {$box, $personal} = setup_settings_panel();
        const requests = capture_get();
        let personal_data;
        mock_template(PERSONAL_TEMPLATE, false, (data) => {
            personal_data = data;
            return "<personal>";
        });

        email_addresses.refresh(sub);
        assert.ok(!$box.visible());
        assert.equal($personal.html(), "<personal>");
        assert.deepEqual(personal_data, {
            has_address: false,
            is_enabled: true,
            can_generate: false,
        });
        assert.equal(requests.length, 0);
    },
);

run_test("refresh without an address renders the generate button", ({override, mock_template}) => {
    override(stream_data, "can_administer_channel", () => false);
    override(stream_data, "can_post_messages_in_stream", () => true);
    const {$personal} = setup_settings_panel();
    const requests = capture_get();
    let personal_data;
    mock_template(PERSONAL_TEMPLATE, false, (data) => {
        personal_data = data;
        return "<personal>";
    });

    email_addresses.refresh(sub);
    requests[0].success({email_addresses: []});
    assert.equal($personal.html(), "<personal>");
    assert.deepEqual(personal_data, {
        has_address: false,
        is_enabled: true,
        can_generate: true,
        address: undefined,
        address_id: undefined,
    });
});

run_test(
    "generate buttons are hidden while bot addresses are not allowed",
    ({override, mock_template}) => {
        override(stream_data, "can_administer_channel", () => true);
        override(stream_data, "can_post_messages_in_stream", () => true);
        override(
            stream_data,
            "get_current_user_and_their_bots_with_post_messages_permission",
            () => [me],
        );
        sub.miatsuco_allow_email_posting = false;
        sub.miatsuco_allow_user_email_posting = false;
        const {$box} = setup_settings_panel();
        const requests = capture_get();
        let list_data;
        mock_template(LIST_TEMPLATE, false, (data) => {
            list_data = data;
            return "<list>";
        });
        mock_template(PERSONAL_TEMPLATE, false, () => "<personal>");

        email_addresses.refresh(sub);
        assert.ok(!$box.visible());
        requests[0].success({email_addresses: []});
        assert.equal(list_data.has_addresses, false);
        assert.deepEqual(list_data.slots, []);
        assert.ok(!$box.visible());

        email_addresses.refresh(sub);
        assert.ok(!$box.visible());
        requests[1].success({email_addresses: [address({id: 1, sender_id: gateway_bot.user_id})]});
        assert.ok($box.visible());

        sub.miatsuco_allow_email_posting = true;
        sub.miatsuco_allow_user_email_posting = true;
    },
);

function click_handler(selector) {
    email_addresses.initialize();
    return $("#channels_overlay_container").get_on_handler("click", selector);
}

function link_button_to_panel(button_selector) {
    const $button = $(button_selector);
    const $panel = $(SETTINGS_SELECTOR);
    $panel.attr("data-stream-id", "10");
    $button.set_closest_results(".subscription_settings", $panel);
    return $button;
}

run_test(
    "generate button requests an address for the clicked sender",
    ({override, mock_template}) => {
        override(stream_data, "can_administer_channel", () => true);
        override(stream_data, "can_post_messages_in_stream", () => false);
        const handler = click_handler(".miatsuco-generate-email-address");
        const $button = link_button_to_panel(".miatsuco-generate-email-address");
        const $subsection = $.create("generate subsection");
        const $status = $.create("status");
        $button.set_closest_results(".subsection-parent, .settings-subsection-parent", $subsection);
        $subsection.set_find_results(".alert-notification", $status);
        const $row = $.create("generate row");
        $row.attr("data-sender-id", "5");
        $button.set_closest_results("[data-sender-id]", $row);
        setup_settings_panel();
        mock_template(PERSONAL_TEMPLATE, false, () => "<personal>");

        const requests = capture_get();
        let prevented = false;
        let stopped = false;
        handler.call(".miatsuco-generate-email-address", {
            preventDefault() {
                prevented = true;
            },
            stopPropagation() {
                stopped = true;
            },
        });
        assert.ok(prevented && stopped);
        assert.equal(requests[0].url, "/json/streams/10/email_address");
        assert.deepEqual(requests[0].data, {sender_id: 5});

        requests[0].success();
        assert.equal(requests.length, 2);
        assert.equal(requests[1].url, "/json/streams/10/email_addresses");

        let error_args;
        ui_report.error = (...args) => {
            error_args = args;
        };
        requests[0].error({status: 400});
        assert.equal(error_args[2][0], $status[0]);

        const $personal_button = link_button_to_panel(".miatsuco-generate-email-address");
        $personal_button.set_closest_results("[data-sender-id]", []);
        handler.call(".miatsuco-generate-email-address", {
            preventDefault() {},
            stopPropagation() {},
        });
        assert.deepEqual(requests[2].data, {sender_id: 1});
    },
);

run_test("revoke button confirms and deletes the address", ({override}) => {
    override(stream_data, "can_administer_channel", () => true);
    override(stream_data, "can_post_messages_in_stream", () => true);
    const handler = click_handler(".miatsuco-revoke-email-address");
    const $button = link_button_to_panel(".miatsuco-revoke-email-address");
    const $card = $.create("address card");
    $card.attr("data-email-address-id", "7");
    $button.set_closest_results("[data-email-address-id]", $card);
    setup_settings_panel();

    let dialog;
    confirm_dialog.launch = (conf) => {
        dialog = conf;
    };
    handler.call(".miatsuco-revoke-email-address", {
        preventDefault() {},
        stopPropagation() {},
    });
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
});
