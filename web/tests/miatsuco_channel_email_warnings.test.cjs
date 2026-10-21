"use strict";

const assert = require("node:assert/strict");

const {make_stream} = require("./lib/example_stream.cjs");
const {$t} = require("./lib/i18n.cjs");
const {mock_esm, zrequire} = require("./lib/namespace.cjs");
const {run_test} = require("./lib/test.cjs");
const $ = require("./lib/zjquery.cjs");

mock_esm("../src/compose_banner", {WARNING: "warning"});

const settings_components = zrequire("settings_components");

function make_checkbox(id, checked) {
    const $checkbox = $.create(id);
    $checkbox.attr("id", id);
    $checkbox.set_matches(":checked", checked);
    return $checkbox;
}

run_test(
    "email posting warnings follow the saved setting and the checkbox",
    ({mock_template, override_rewire}) => {
        const $subsection = $.create("general subsection");
        const $banner = $.create("warning banner");
        $subsection.set_find_results(".stream-general-settings-warning-banner", $banner);
        const rendered = [];
        mock_template("compose_banner/compose_banner.hbs", false, (data) => {
            assert.equal(data.banner_type, "warning");
            rendered.push(data.banner_text);
            return "<banner>";
        });
        const checked = new Map();
        override_rewire(settings_components, "get_input_element_value", (elem) =>
            checked.get(elem),
        );

        const $user_checkbox = make_checkbox("id_miatsuco_allow_user_email_posting", false);
        const $bot_checkbox = make_checkbox("id_miatsuco_allow_email_posting", true);
        const $other_input = make_checkbox("id_name", false);
        checked.set($user_checkbox[0], false);
        checked.set($bot_checkbox[0], true);
        checked.set($other_input[0], false);
        const elements = [$user_checkbox[0], $bot_checkbox[0], $other_input[0]];
        const saved_sub = make_stream({
            miatsuco_allow_user_email_posting: true,
            miatsuco_allow_email_posting: true,
        });

        settings_components.update_email_posting_disable_warnings($subsection, saved_sub, elements);
        assert.deepEqual(rendered, [
            $t({
                defaultMessage:
                    "Saving this change revokes every personal email address for this channel.",
            }),
        ]);

        rendered.length = 0;
        checked.set($bot_checkbox[0], false);
        settings_components.update_email_posting_disable_warnings($subsection, saved_sub, elements);
        assert.deepEqual(rendered, [
            $t({
                defaultMessage:
                    "Saving this change revokes every personal email address for this channel.",
            }),
            $t({
                defaultMessage:
                    "Saving this change revokes every bot email address for this channel.",
            }),
        ]);

        const unsaved_sub = make_stream({
            miatsuco_allow_user_email_posting: false,
            miatsuco_allow_email_posting: false,
        });
        rendered.length = 0;
        settings_components.update_email_posting_disable_warnings(
            $subsection,
            unsaved_sub,
            elements,
        );
        assert.deepEqual(rendered, []);
    },
);
