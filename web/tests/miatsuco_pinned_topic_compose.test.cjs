"use strict";

const assert = require("node:assert/strict");

const {mock_banners} = require("./lib/compose_banner.cjs");
const {make_user_group} = require("./lib/example_group.cjs");
const {make_realm} = require("./lib/example_realm.cjs");
const {make_user, Role} = require("./lib/example_user.cjs");
const {$t} = require("./lib/i18n.cjs");
const {mock_esm, zrequire} = require("./lib/namespace.cjs");
const {run_test} = require("./lib/test.cjs");
const $ = require("./lib/zjquery.cjs");

mock_esm("../src/channel");
mock_esm("../src/group_permission_settings", {
    get_group_permission_setting_config: () => ({
        allow_everyone_group: true,
    }),
});

const compose_banner = zrequire("compose_banner");
const compose_state = zrequire("compose_state");
const compose_validate = zrequire("compose_validate");
const people = zrequire("people");
const {set_current_user, set_realm} = zrequire("state_data");
const stream_data = zrequire("stream_data");
const user_groups = zrequire("user_groups");
const {initialize_user_settings} = zrequire("user_settings");

const realm = make_realm({
    realm_empty_topic_display_name: "general chat",
    realm_topics_policy: "allow_empty_topic",
});
set_realm(realm);
const current_user = {};
set_current_user(current_user);
initialize_user_settings({user_settings: {default_language: "en"}});

const me = make_user({
    email: "me@example.com",
    user_id: 30,
    full_name: "Me Myself",
    date_joined: new Date(),
});

const bob = make_user({
    email: "bob@example.com",
    user_id: 32,
    full_name: "Bob",
    role: Role.ADMINISTRATOR,
});

people.init();
people.add_active_user(me);
people.initialize_current_user(me.user_id);
people.add_active_user(bob);

const nobody = make_user_group({
    name: "role:nobody",
    id: 1,
    members: new Set(),
    is_system_group: true,
    direct_subgroup_ids: new Set(),
});
const everyone = make_user_group({
    name: "role:everyone",
    id: 2,
    members: new Set([30]),
    is_system_group: true,
    direct_subgroup_ids: new Set([5]),
});
const admin = make_user_group({
    name: "role:administrators",
    id: 3,
    members: new Set([32]),
    is_system_group: true,
    direct_subgroup_ids: new Set(),
});
const moderators = make_user_group({
    name: "role:moderators",
    id: 4,
    members: new Set(),
    is_system_group: true,
    direct_subgroup_ids: new Set([3]),
});
const members = make_user_group({
    name: "role:members",
    id: 5,
    members: new Set(),
    is_system_group: true,
    direct_subgroup_ids: new Set([4]),
});

user_groups.initialize({realm_user_groups: [nobody, everyone, admin, moderators, members]});

function test_ui(label, f) {
    run_test(label, (helpers) => {
        $("textarea#compose-textarea").val("some message");
        return f(helpers);
    });
}

test_ui("test_pinned_topic_posting_permission", ({mock_template, override}) => {
    mock_banners();

    override(current_user, "user_id", 30);
    const sub = {
        stream_id: 103,
        name: "stream103",
        subscribed: true,
        can_send_message_group: everyone.id,
        can_create_topic_group: everyone.id,
        can_add_subscribers_group: everyone.id,
        miatsuco_can_post_in_pinned_topic_group: admin.id,
    };
    stream_data.add_sub_for_tests(sub);
    compose_state.set_message_type("stream");
    compose_state.set_stream_id(sub.stream_id);
    $("#send_message_form").set_find_results(".message-textarea", $("textarea#compose-textarea"));

    compose_state.topic("plans");
    assert.ok(compose_validate.validate());

    let banner_text;
    mock_template("compose_banner/compose_banner.hbs", false, (data) => {
        assert.equal(data.classname, compose_banner.CLASSNAMES.no_post_permissions);
        banner_text = data.banner_text;
        return "<banner-stub>";
    });
    compose_state.topic("📌 plans");
    assert.ok(!compose_validate.validate());
    assert.equal(
        banner_text,
        $t({defaultMessage: "You do not have permission to post in the pinned topic."}),
    );

    override(current_user, "user_id", 32);
    banner_text = undefined;
    assert.ok(compose_validate.validate());
    assert.equal(banner_text, undefined);
});

test_ui("test_pinned_topic_start_permission", ({mock_template, override}) => {
    mock_banners();
    const stream_topic_history = zrequire("stream_topic_history");

    override(current_user, "user_id", 30);
    const sub = {
        stream_id: 104,
        name: "stream104",
        subscribed: true,
        can_send_message_group: everyone.id,
        can_create_topic_group: everyone.id,
        can_add_subscribers_group: everyone.id,
        can_administer_channel_group: admin.id,
        miatsuco_can_post_in_pinned_topic_group: everyone.id,
    };
    stream_data.add_sub_for_tests(sub);
    stream_topic_history.mark_history_fetched_for(sub.stream_id);
    compose_state.set_message_type("stream");
    compose_state.set_stream_id(sub.stream_id);
    $("#send_message_form").set_find_results(".message-textarea", $("textarea#compose-textarea"));

    let banner_text;
    mock_template("compose_banner/compose_banner.hbs", false, (data) => {
        banner_text = data.banner_text;
        return "<banner-stub>";
    });
    compose_state.topic("📌 fresh");
    assert.ok(!compose_validate.validate());
    assert.equal(
        banner_text,
        $t({defaultMessage: "Only channel administrators can start a pinned topic."}),
    );

    stream_topic_history.add_message({
        stream_id: sub.stream_id,
        message_id: 1,
        topic_name: "📌 fresh",
    });
    banner_text = undefined;
    assert.ok(compose_validate.validate());
    assert.equal(banner_text, undefined);

    compose_state.topic("📌 other");
    override(current_user, "user_id", 32);
    assert.ok(compose_validate.validate());
});
