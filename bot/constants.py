from __future__ import annotations

LOCK_TYPES: tuple[str, ...] = (
    "link",
    "media",
    "photo",
    "video",
    "sticker",
    "gif",
    "forward",
    "mention",
    "voice",
    "document",
    "bots",
)

PUNISH_MODES: tuple[str, ...] = ("mute", "kick", "ban")

WARN_LIMITS: tuple[int, ...] = (2, 3, 5, 7, 10)

FLOOD_LIMITS: tuple[int, ...] = (0, 5, 8, 10, 15)

HELP_CATEGORIES: tuple[str, ...] = (
    "admin",
    "warns",
    "notes",
    "filters",
    "locks",
    "greetings",
    "antiflood",
    "ai",
    "alias",
    "roles",
    "misc",
)

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"

BOT_RIGHTS: tuple[str, ...] = (
    "ban",
    "mute",
    "warn",
    "delete",
    "pin",
    "promote",
    "settings",
    "locks",
    "notes",
    "ai",
    "alias",
    "perms",
)

RIGHT_SOURCES: dict[str, str] = {
    "ban": "can_restrict_members",
    "mute": "can_restrict_members",
    "warn": "can_restrict_members",
    "delete": "can_delete_messages",
    "pin": "can_pin_messages",
    "promote": "can_promote_members",
    "settings": "can_change_info",
    "locks": "can_delete_messages",
    "notes": "",
    "ai": "",
    "alias": "",
    "perms": "never",
}

MEMBER_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "messages": ("can_send_messages",),
    "media": ("can_send_photos", "can_send_videos", "can_send_audios", "can_send_documents"),
    "other": ("can_send_other_messages", "can_send_voice_notes", "can_send_video_notes"),
    "polls": ("can_send_polls",),
    "links": ("can_add_web_page_previews",),
    "invite": ("can_invite_users",),
    "pin": ("can_pin_messages",),
    "info": ("can_change_info",),
}

MUTED_PERMISSIONS = {
    "can_send_messages": False,
    "can_send_audios": False,
    "can_send_documents": False,
    "can_send_photos": False,
    "can_send_videos": False,
    "can_send_video_notes": False,
    "can_send_voice_notes": False,
    "can_send_polls": False,
    "can_send_other_messages": False,
    "can_add_web_page_previews": False,
    "can_change_info": False,
    "can_invite_users": True,
    "can_pin_messages": False,
}

UNMUTED_PERMISSIONS = {
    "can_send_messages": True,
    "can_send_audios": True,
    "can_send_documents": True,
    "can_send_photos": True,
    "can_send_videos": True,
    "can_send_video_notes": True,
    "can_send_voice_notes": True,
    "can_send_polls": True,
    "can_send_other_messages": True,
    "can_add_web_page_previews": True,
    "can_change_info": False,
    "can_invite_users": True,
    "can_pin_messages": False,
}
