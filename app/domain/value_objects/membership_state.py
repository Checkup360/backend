import enum


class MembershipState(str, enum.Enum):
    """Whether an organization membership still grants access.

    A membership is active while it holds at least one role. Deactivating a
    user removes all their roles, which makes the membership inactive while
    keeping it (and its history) in the organization.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    ALL = "all"
