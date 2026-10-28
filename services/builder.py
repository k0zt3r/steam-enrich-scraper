from urllib.parse import urlparse

from models.game import SourceGame, SteamData, GamePayload, Requirements
from services.links import filter_archive_links


class GameBuilder:
    """Merge a scraped SourceGame with Steam metadata into a GamePayload."""

    def build(self, source: SourceGame, steam: SteamData) -> GamePayload:

        # Prefer the canonical Steam title; the caller guarantees Steam data
        # is present (otherwise validate() rejects the empty title).
        title = steam.name

        description = steam.description or source.description

        # Release notes (edition/install steps) only exist at the source;
        # Steam has no such notion.
        release_notes = source.release_notes

        # Build version is a source-only field as well.
        version = source.version

        developer = steam.developer or ""
        publisher = steam.publisher or ""
        poster = steam.poster or source.poster
        trailer = steam.trailer
        screenshots = steam.screenshots

        # Single point of link filtering, regardless of where the links came
        # from (static HTML, headless browser, a future source...). The source
        # domain is passed so a link hosted on the source site itself is not
        # dropped as an unknown host.
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
