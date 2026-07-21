from dataclasses import dataclass


@dataclass(frozen=True)
class Grant:
    subject: str
    permission: str


def is_allowed(grants: list[Grant], subject: str, permission: str) -> bool:
    return Grant(subject, permission) in grants
