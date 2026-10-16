import _ from "lodash";
import * as z from "zod/mini";

import * as buttons from "./buttons.ts";
import * as channel from "./channel.ts";
import * as stream_data from "./stream_data.ts";
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
    let new_topic_name;
    if (is_pinned(old_topic_name)) {
        new_topic_name = display_parts(old_topic_name)[1];
    } else {
        new_topic_name = PINNED_TOPIC_PREFIX + old_topic_name;
    }

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
            if (xhr.responseJSON) {
                const {msg} = z.object({msg: z.string()}).parse(xhr.responseJSON);
                ui_report.generic_embed_error(_.escape(msg), 3500);
            }
        },
    });
}
