import $ from "jquery";
import assert from "minimalistic-assert";
import * as z from "zod/mini";

import render_channel_email_addresses from "../templates/stream_settings/miatsuco_channel_email_addresses.hbs";

import * as channel from "./channel.ts";
import * as confirm_dialog from "./confirm_dialog.ts";
import * as dialog_widget from "./dialog_widget.ts";
import {$t, $t_html} from "./i18n.ts";
import * as people from "./people.ts";
import * as stream_settings_containers from "./stream_settings_containers.ts";
import type {StreamSubscription} from "./sub_store.ts";
import * as sub_store from "./sub_store.ts";
import * as timerender from "./timerender.ts";

const email_address_schema = z.object({
    id: z.number(),
    email: z.nullable(z.string()),
    creator_id: z.nullable(z.number()),
    sender_id: z.number(),
    date_created: z.number(),
});

const email_addresses_response_schema = z.object({
    email_addresses: z.array(email_address_schema),
});

function get_full_name(user_id: number | null): string {
    const user = user_id === null ? undefined : people.maybe_get_user_by_id(user_id, true);
    if (user === undefined) {
        return $t({defaultMessage: "Unknown user"});
    }
    return user.full_name;
}

function get_sender_label(sender_id: number): string {
    if (sender_id === people.EMAIL_GATEWAY_BOT.user_id) {
        return $t({defaultMessage: "Email Gateway bot"});
    }
    return get_full_name(sender_id);
}

export function refresh(sub: StreamSubscription): void {
    const $list = stream_settings_containers
        .get_edit_container(sub)
        .find(".miatsuco-email-addresses-list");

    void channel.get({
        url: `/json/streams/${sub.stream_id}/email_addresses`,
        success(data) {
            const {email_addresses} = email_addresses_response_schema.parse(data);
            $list.html(
                render_channel_email_addresses({
                    has_addresses: email_addresses.length > 0,
                    email_addresses: email_addresses.map((address) => ({
                        id: address.id,
                        address: address.email ?? "",
                        sender_name: get_sender_label(address.sender_id),
                        creator_name: get_full_name(address.creator_id),
                        created_date: timerender.absolute_time(address.date_created * 1000),
                    })),
                }),
            );
        },
    });
}

function get_sub_for_element($element: JQuery): StreamSubscription {
    const stream_id = Number.parseInt(
        $element.closest(".subscription_settings").attr("data-stream-id")!,
        10,
    );
    const sub = sub_store.get(stream_id);
    assert(sub !== undefined);
    return sub;
}

export function initialize(): void {
    $("#channels_overlay_container").on(
        "click",
        ".miatsuco-revoke-email-address",
        function (this: HTMLElement, e) {
            e.preventDefault();
            e.stopPropagation();

            const $address = $(this).closest("[data-email-address-id]");
            const email_address_id = Number.parseInt($address.attr("data-email-address-id")!, 10);
            const sub = get_sub_for_element($(this));

            const url = `/json/streams/${sub.stream_id}/email_addresses/${email_address_id}`;
            const opts = {
                success_continuation() {
                    refresh(sub);
                },
            };

            confirm_dialog.launch({
                modal_title_html: $t_html({defaultMessage: "Revoke email address?"}),
                modal_content_html: $t_html({
                    defaultMessage:
                        "Anyone using this address will no longer be able to message the channel by email.",
                }),
                modal_submit_button_text: $t({defaultMessage: "Revoke"}),
                id: "confirm_revoke_channel_email_address_modal",
                on_click() {
                    dialog_widget.submit_api_request(channel.del, url, {}, opts);
                },
                loading_spinner: true,
            });
        },
    );
}
