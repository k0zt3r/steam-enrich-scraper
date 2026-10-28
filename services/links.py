from urllib.parse import urlparse


# Единственное место, где перечислены разрешённые хосты для скачивания.
# Любой парсер или скрапер может вернуть что угодно; GameBuilder.build()
# один раз прогоняет ссылки через filter_archive_links(), поэтому дублировать
# проверку в каждом источнике не нужно. Замени на хосты, которым доверяет
# твой собственный пайплайн.
ALLOWED_ARCHIVE_HOSTS = (
    "files.example.com",
    "cdn.example.com",
    "mirror.example.net",
)


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _normalize_host(host: str) -> str:
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_allowed_archive_host(link_url: str) -> bool:
    host = _normalize_host(urlparse(link_url).netloc)
    return any(_host_matches(host, allowed) for allowed in ALLOWED_ARCHIVE_HOSTS)


def filter_archive_links(links, source_domain: str = "") -> list:
    """
    Оставляем только те ссылки, которые готовы опубликовать: magnet / прямой
    .torrent, ссылки на разрешённом хосте или ссылки на самом сайте-источнике.

    source_domain — домен страницы игры. Ссылка на том же домене считается
    доверенной сама по себе; это важно для источников, которые отдают файл
    напрямую, а не через сторонний файлообменник.
    """

    source_domain = _normalize_host(source_domain) if source_domain else ""

    filtered = []

    for link in (links or []):

        if (
            link.startswith("magnet:")
            or urlparse(link).path.lower().endswith(".torrent")
        ):
            filtered.append(link)
            continue

        if is_allowed_archive_host(link):
            filtered.append(link)
            continue

        if source_domain:
            link_host = _normalize_host(urlparse(link).netloc)
            if _host_matches(link_host, source_domain):
                filtered.append(link)

    if not filtered:
        print("подходящих ссылок на скачивание нет — выбери вручную")

    return filtered
