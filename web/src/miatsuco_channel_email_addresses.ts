import $ from "jquery";
import assert from "minimalistic-assert";
import * as z from "zod/mini";

import render_channel_email_addresses from "../templates/stream_settings/miatsuco_channel_email_addresses.hbs";
import render_personal_channel_email from "../templates/stream_settings/miatsuco_personal_channel_email.hbs";

import * as channel from "./channel.ts";
import * as confirm_dialog from "./confirm_dialog.ts";
import * as dialog_widget from "./dialog_widget.ts";
import {$t, $t_html} from "./i18n.ts";
import * as people from "./people.ts";
import {current_user} from "./state_data.ts";
import * as stream_data from "./stream_data.ts";
import * as stream_settings_containers from "./stream_settings_containers.ts";
import type {StreamSubscription} from "./sub_store.ts";
import * as sub_store from "./sub_store.ts";
import * as timerender from "./timerender.ts";
import * as ui_report from "./ui_report.ts";

const email_address_schema = z.object({
    id: z.number(),
    email: z.nullable(z.string()),
    creator_id: z.nullable(z.number()),
    sender_id: z.number(),
    is_personal: z.boolean(),
    date_created: z.number(),
});

const email_addresses_response_schema = z.object({
    email_addresses: z.array(email_address_schema),
});

type EmailAddress = z.infer<typeof email_address_schema>;

function get_container(sub: StreamSubscription): JQuery {
    return stream_settings_containers.get_edit_container(sub).find(".miatsuco-email-addresses-box");
}

function get_full_name(user_id: number | null): string {
    const user = user_id === null ? undefined : people.maybe_get_user_by_id(user_id, true);
    if (user === undefined) {
        return $t({defaultMessage: "Unknown user"});
    }
    return user.full_name;
}

function get_email_address_tags(): {name: string; description: string}[] {
    return [
        {
            name: "show-sender",
            description: $t({
                defaultMessage: "The sender's email address",
            }),
        },
        {
            name: "include-footer",
            description: $t({defaultMessage: "Email footers (e.g., signature)"}),
        },
        {
            name: "include-quotes",
            description: $t({defaultMessage: "Quoted original email (in replies)"}),
        },
        {
            name: "prefer-html",
            description: $t({
                defaultMessage: "Use html encoding (not recommended)",
            }),
        },
    ];
}

function get_sender_label(sender_id: number): string {
    if (sender_id === people.EMAIL_GATEWAY_BOT.user_id) {
        return $t({defaultMessage: "Email Gateway bot"});
    }
    return get_full_name(sender_id);
}

function get_address_card_data(address: EmailAddress): Record<string, unknown> {
    const is_personal = address.is_personal;
    const email = address.email ?? "";
    return {
        is_empty: false,
        id: address.id,
        email,
        address: is_personal ? "" : email,
        sender_name: get_sender_label(address.sender_id),
        creator_name: get_full_name(address.creator_id),
        created_date: timerender.absolute_time(address.date_created * 1000),
        has_options: !is_personal && email !== "",
        tags: get_email_address_tags().map((tag) => ({
            ...tag,
            id: `email-address-${address.id}-${tag.name}`,
            checked: tag.name === "show-sender",
        })),
    };
}

function get_sender_ids(sub: StreamSubscription): number[] {
    const bot_ids = stream_data
        .get_current_user_and_their_bots_with_post_messages_permission(sub)
        .filter((sender) => sender.user_id !== current_user.user_id)
        .map((sender) => sender.user_id);
    return [people.EMAIL_GATEWAY_BOT.user_id, ...bot_ids];
}

function get_sender_slots(
    sub: StreamSubscription,
    sender_ids: number[],
    own_addresses: EmailAddress[],
): Record<string, unknown>[] {
    const can_generate =
        stream_data.can_post_messages_in_stream(sub) && sub.miatsuco_allow_email_posting;

    const slots: Record<string, unknown>[] = [];
    for (const sender_id of sender_ids) {
        const address = own_addresses.find((own_address) => own_address.sender_id === sender_id);
        if (address !== undefined) {
            slots.push(get_address_card_data(address));
        } else if (can_generate) {
            slots.push({is_empty: true, sender_id, sender_name: get_sender_label(sender_id)});
        }
    }
    const leftover_addresses = own_addresses.filter(
        (address) => !sender_ids.includes(address.sender_id),
    );
    return [...leftover_addresses.map((address) => get_address_card_data(address)), ...slots];
}

function render_address_list(
    sub: StreamSubscription,
    $container: JQuery,
    email_addresses: EmailAddress[],
): void {
    const bot_addresses = email_addresses.filter((address) => !address.is_personal);
    const own_bot_addresses = bot_addresses.filter(
        (address) => address.creator_id === current_user.user_id,
    );
    const others = bot_addresses
        .filter((address) => address.creator_id !== current_user.user_id)
        .map((address) => get_address_card_data(address));
    const personal_addresses = email_addresses.filter((address) => address.is_personal);
    const personal = [
        ...personal_addresses.filter((address) => address.creator_id === current_user.user_id),
        ...personal_addresses.filter((address) => address.creator_id !== current_user.user_id),
    ].map((address) => get_address_card_data(address));
    const slots = get_sender_slots(sub, get_sender_ids(sub), own_bot_addresses);
    const has_bot_addresses = slots.length > 0 || others.length > 0;
    const has_personal_addresses = personal.length > 0;
    $container.find(".miatsuco-email-addresses-list").html(
        render_channel_email_addresses({
            has_addresses: has_bot_addresses || has_personal_addresses,
            has_bot_addresses,
            slots,
            others,
            has_personal_addresses,
            personal,
        }),
    );
}

export function refresh(sub: StreamSubscription): void {
    const can_administer = stream_data.can_administer_channel(sub);
    const is_enabled = sub.miatsuco_allow_user_email_posting;
    const can_generate_personal = is_enabled && stream_data.can_post_messages_in_stream(sub);
    const has_enabled_setting = is_enabled || sub.miatsuco_allow_email_posting;
    const $container = get_container(sub);
    const $personal_content = stream_settings_containers
        .get_edit_container(sub)
        .find(".miatsuco-personal-email-content");

    $container.toggle(can_administer && has_enabled_setting);
    if (!can_generate_personal) {
        $personal_content.html(
            render_personal_channel_email({has_address: false, is_enabled, can_generate: false}),
        );
    }
    if (!can_administer && !can_generate_personal) {
        return;
    }

    void channel.get({
        url: `/json/streams/${sub.stream_id}/email_addresses`,
        success(data) {
            const {email_addresses} = email_addresses_response_schema.parse(data);
            if (can_administer) {
                render_address_list(sub, $container, email_addresses);
                $container.toggle(has_enabled_setting || email_addresses.length > 0);
            }
            if (can_generate_personal) {
                const own_address = email_addresses.find(
                    (address) => address.is_personal && address.creator_id === current_user.user_id,
                );
                $personal_content.html(
                    render_personal_channel_email({
                        has_address: own_address !== undefined,
                        is_enabled,
                        can_generate: true,
                        address: own_address?.email,
                        address_id: own_address?.id,
                    }),
                );
            }
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
        ".miatsuco-generate-email-address",
        function (this: HTMLElement, e) {
            e.preventDefault();
            e.stopPropagation();

            const sub = get_sub_for_element($(this));
            const $status = $(this)
                .closest(".subsection-parent, .settings-subsection-parent")
                .find(".alert-notification");
            const $sender = $(this).closest("[data-sender-id]");
            const sender_id =
                $sender.length > 0
                    ? Number.parseInt($sender.attr("data-sender-id")!, 10)
                    : current_user.user_id;
            void channel.get({
                url: `/json/streams/${sub.stream_id}/email_address`,
                data: {sender_id},
                success() {
                    refresh(sub);
                },
                error(xhr) {
                    ui_report.error($t_html({defaultMessage: "Failed"}), xhr, $status);
                },
            });
        },
    );

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
