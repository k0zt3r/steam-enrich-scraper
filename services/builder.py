from urllib.parse import urlparse

from models.game import SourceGame, SteamData, GamePayload, Requirements
from services.links import filter_archive_links


class GameBuilder:
    """Объединяет распарсенный SourceGame с данными Steam в GamePayload."""

    def build(self, source: SourceGame, steam: SteamData) -> GamePayload:

        # Каноническое название берём из Steam; вызывающий код гарантирует,
        # что данные Steam есть (иначе validate() отсечёт пустое название).
        title = steam.name

        description = steam.description or source.description

        # Примечания к релизу (издание/шаги установки) есть только у источника,
        # у Steam такого понятия нет.
        release_notes = source.release_notes

        # Версия сборки — тоже поле только источника.
        version = source.version

        developer = steam.developer or ""
        publisher = steam.publisher or ""
        poster = steam.poster or source.poster
        trailer = steam.trailer
        screenshots = steam.screenshots

        # Единая точка фильтрации ссылок — неважно, откуда они пришли
        # (статичный HTML, headless-браузер, будущий источник...). Домен
        # источника передаём, чтобы не отсечь ссылку, которую хостит сам
        # сайт-источник, как «неизвестный хост».
        download_links = filter_archive_links(
            source.download_links,
            source_domain=urlparse(source.url).netloc,
        )

        requirements = self.merge_requirements(
            source.requirements,
            steam.requirements,
        )

        return GamePayload(
            title=title,
            steam_url=source.steam_url,
            steam_appid=steam.appid,
            source_url=source.url,
            download_links=download_links,
            archive_size=source.size,
            is_adult=source.is_adult,
            description=description,
            release_notes=release_notes,
            version=version,
            developer=developer,
            publisher=publisher,
            poster=poster,
            trailer=trailer,
            screenshots=screenshots,
            requirements=requirements,
        )

    def merge_requirements(self, source, steam) -> Requirements:
        return Requirements(
            os=steam.os or source.os,
            cpu=steam.cpu or source.cpu,
            ram=steam.ram or source.ram,
            gpu=steam.gpu or source.gpu,
            storage=steam.storage or source.storage,
        )
