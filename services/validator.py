from models.game import GamePayload


def validate(payload: GamePayload) -> list[str]:
    """Return a list of human-readable problems; empty means the record is OK."""

    errors = []

    if not payload.title:
        errors.append("missing title")

    if not payload.steam_appid:
        errors.append("missing Steam appid")

    if not payload.download_links:
        errors.append("no download links")

    return errors
