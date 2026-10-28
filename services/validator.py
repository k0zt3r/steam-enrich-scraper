from models.game import GamePayload


def validate(payload: GamePayload) -> list[str]:
    """Вернуть список проблем в читаемом виде; пустой список — запись в порядке."""

    errors = []

    if not payload.title:
        errors.append("нет названия")

    if not payload.steam_appid:
        errors.append("нет Steam appid")

    if not payload.download_links:
        errors.append("нет ссылок на скачивание")

    return errors
