from urllib.parse import urlparse


# The single place where allowed download hosts are listed. Any parser or
# scraper may return arbitrary links; GameBuilder.build() runs them through
# filter_archive_links() once, so there is no need to duplicate this check
# in every source. Replace these with the hosts your own pipeline trusts.
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
    Keep only links we are willing to publish: magnet / direct .torrent,
    links on an allowed host, or links on the source site itself.

    source_domain is the domain of the game page. A link on that same
    domain is trusted on its own, which matters for sources that host the
    download directly instead of via a third-party file host.
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
        print("no acceptable download link found - pick one manually")

    return filtered
