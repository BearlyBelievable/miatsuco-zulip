import * as buttons from "./buttons.ts";
import * as channel from "./channel.ts";
import {$t} from "./i18n.ts";
import {realm} from "./state_data.ts";
import * as stream_data from "./stream_data.ts";
import * as stream_topic_history from "./stream_topic_history.ts";
import * as ui_report from "./ui_report.ts";

// Mirrors PINNED_TOPIC_PREFIX in zerver/lib/miatsuco_pinned_topic_name.py.
export const PINNED_TOPIC_PREFIX = "📌 ";

export function is_pinned(topic_name: string): boolean {
    return topic_name.startsWith(PINNED_TOPIC_PREFIX);
}

export function display_parts(topic_name: string): [string, string] {
    if (is_pinned(topic_name)) {
        return [PINNED_TOPIC_PREFIX, topic_name.slice(PINNED_TOPIC_PREFIX.length)];
    }
    return ["", topic_name];
}

export function pin_name(topic_name: string): string {
    return PINNED_TOPIC_PREFIX + topic_name;
}

export function unpin_name(topic_name: string): string {
    return display_parts(topic_name)[1];
}

function get_lowercase_topic_names(stream_id: number): Set<string> {
    return new Set(
        stream_topic_history.get_recent_topic_names(stream_id).map((name) => name.toLowerCase()),
    );
}

export function is_local_echo_safe(stream_id: number, topic_name: string): boolean {
    if (get_lowercase_topic_names(stream_id).has(topic_name.toLowerCase())) {
        return true;
    }
    return (
        stream_topic_history.has_history_for(stream_id) &&
        pin_name(unpin_name(topic_name)).length <= realm.max_topic_length
    );
}

export function resolve_topic_name(stream_id: number, topic_name: string): string {
    const existing_topic_names = get_lowercase_topic_names(stream_id);
    if (existing_topic_names.has(topic_name.toLowerCase())) {
        return topic_name;
    }
    const bare_name = unpin_name(topic_name);
    return (
        [bare_name, pin_name(bare_name)].find((name) =>
            existing_topic_names.has(name.toLowerCase()),
        ) ?? topic_name
    );
}

export function user_can_post_in_topic(stream_id: number, topic_name: string): boolean {
    const sub = stream_data.get_sub_by_id(stream_id);
    if (sub !== undefined && is_pinned(topic_name)) {
        return stream_data.can_post_in_pinned_topic(sub);
    }
    return true;
}

export function user_can_rename_topic(stream_id: number, topic_name: string): boolean {
    const sub = stream_data.get_sub_by_id(stream_id);
    if (sub !== undefined && is_pinned(topic_name)) {
        return stream_data.can_administer_channel(sub);
    }
    return true;
}

export function pinned_first(topic_names: string[]): string[] {
    return [
        ...topic_names.filter((topic_name) => is_pinned(topic_name)),
        ...topic_names.filter((topic_name) => !is_pinned(topic_name)),
    ];
}

// Mirrors topic_pin_toggled in zerver/lib/miatsuco_pinned_topic_name.py.
export function topic_pin_toggled(new_topic: string, original_topic: string): boolean {
    if (is_pinned(new_topic) && display_parts(new_topic)[1] === original_topic) {
        return true;
    }
    return is_pinned(original_topic) && display_parts(original_topic)[1] === new_topic;
}

export function toggle_pinned_topic(
    message_id: number,
    old_topic_name: string,
    $row?: JQuery,
): void {
    const new_topic_name = is_pinned(old_topic_name)
        ? unpin_name(old_topic_name)
        : pin_name(old_topic_name);
    const $button = $row?.find(".on_hover_topic_pin, .on_hover_topic_unpin");
    if ($button !== undefined) {
        buttons.show_button_loading_indicator($button);
    }

    void channel.patch({
        url: "/json/messages/" + message_id,
        data: {
            propagate_mode: "change_all",
            topic: new_topic_name,
            send_notification_to_old_thread: false,
            send_notification_to_new_thread: false,
        },
        error(xhr) {
            if ($button !== undefined) {
                buttons.hide_button_loading_indicator($button);
            }
            ui_report.generic_embed_error(
                channel.xhr_error_message(
                    $t({defaultMessage: "Failed to pin or unpin the topic"}),
                    xhr,
                ),
                3500,
            );
        },
    });
}
