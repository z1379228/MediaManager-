from core.site_routing import SiteRoute, classify_site_url


def test_youtube_and_music_share_one_family_with_strict_resource_kinds() -> None:
    assert classify_site_url(
        "https://music.youtube.com/watch?"
        "v=ynUkJsLxStI&list=RDAMVMynUkJsLxStI"
    ) == SiteRoute(
        "youtube",
        "playlist-context",
        "youtube",
        "youtube-search",
    )
    assert classify_site_url(
        "https://www.youtube.com/playlist?list=PL_example"
    ).resource_kind == "playlist"
    assert classify_site_url(
        "https://youtu.be/ynUkJsLxStI"
    ).resource_kind == "video"
    assert classify_site_url(
        "https://www.youtube-nocookie.com/embed/ynUkJsLxStI"
    ) == SiteRoute("youtube", "video", "youtube", "youtube-search")


def test_youtube_route_rejects_ambiguous_or_spoofed_urls() -> None:
    for url in (
        "http://music.youtube.com/watch?v=one",
        'https://music.youtube.com/"watch?v=one&list=PL_example"',
        "https://music.youtube.com/not-watch?v=one&list=PL_example",
        "https://music.youtube.com/watch?v=one&v=two",
        "https://music.youtube.com/watch?v=one&list=PL_a&list=PL_b",
        "https://music.youtube.com/watch?v=one#fragment",
        "https://user@music.youtube.com/watch?v=one",
        "https://music.youtube.com:443/watch?v=one",
        "https://music.youtube.com.evil.test/watch?v=one",
        "https://youtu.be/one?list=PL_example",
        "https://www.youtube-nocookie.com/watch?v=one",
        "https://youtube-nocookie.com/embed/one",
        "https://www.youtube-nocookie.com.evil.test/embed/one",
    ):
        assert classify_site_url(url) is None


def test_other_sites_get_distinct_families_and_provider_roles() -> None:
    assert classify_site_url(
        "https://www.bilibili.com/video/BV1example"
    ) == SiteRoute("bilibili", "video", "bilibili", "bilibili-search")
    assert classify_site_url(
        "https://www.bilibili.com/video/BV1example?spm_id_from=333.1007"
    ).resource_kind == "video"
    assert classify_site_url(
        "https://search.bilibili.com/all?keyword=%E5%B9%BB%E6%9C%88%E7%92%B0"
    ) == SiteRoute("bilibili", "search-page", None, "bilibili-search")
    assert classify_site_url(
        "https://www.facebook.com/reel/123456"
    ) == SiteRoute("facebook", "video-page", "facebook", None)
    assert classify_site_url(
        "https://mega.nz/file/AbCdEf12#abcdefghijklmnop"
    ) == SiteRoute("mega", "public-file", "mega", None)
    assert classify_site_url(
        "https://www.mega.nz/folder/AbCdEf12#abcdefghijklmnop"
    ) == SiteRoute("mega", "public-folder", "mega", None)
    assert classify_site_url(
        "https://ani.gamer.com.tw/animeRef.php?sn=123"
    ) == SiteRoute("ani-gamer", "series", None, "ani-gamer-search")
    assert classify_site_url(
        "https://ani.gamer.com.tw/animeVideo.php?sn=456"
    ) == SiteRoute(
        "ani-gamer",
        "episode",
        None,
        "ani-gamer-episodes",
    )


def test_non_media_pages_do_not_claim_a_download_owner() -> None:
    for url in (
        "https://www.facebook.com/",
        "https://www.bilibili.com/",
        "https://ani.gamer.com.tw/animeRef.php",
        "https://ani.gamer.com.tw/animeVideo.php?sn=not-digits",
    ):
        assert classify_site_url(url) is None


def test_bilibili_search_subdomain_rejects_non_search_or_ambiguous_urls() -> None:
    for url in (
        "https://search.bilibili.com/",
        "https://search.bilibili.com/all",
        "https://search.bilibili.com/all?keyword=",
        "https://search.bilibili.com/all?keyword=%20%20",
        "https://search.bilibili.com/all?keyword=one%7Ftwo",
        "https://search.bilibili.com/all?keyword=one&keyword=two",
        "https://search.bilibili.com/all?keyword=one&page=2",
        "https://search.bilibili.com/video/BV1example?keyword=one",
        "https://search.bilibili.com.evil.test/all?keyword=one",
    ):
        assert classify_site_url(url) is None


def test_facebook_and_mega_routes_reject_ambiguous_or_spoofed_urls() -> None:
    for url in (
        "http://www.facebook.com/reel/123456",
        "https://www.facebook.com/reel/not-a-number",
        "https://www.facebook.com/watch/?v=1&tracking=1",
        "https://www.facebook.com.evil.test/reel/123456",
        "https://mega.nz/file/AbCdEf12",
        "https://mega.nz/file/AbCdEf12?download=1#abcdefghijklmnop",
        "https://mega.nz.evil.test/file/AbCdEf12#abcdefghijklmnop",
        "https://user@mega.nz/file/AbCdEf12#abcdefghijklmnop",
    ):
        assert classify_site_url(url) is None


def test_social_parent_mod_routes_cover_known_official_subdomains() -> None:
    assert classify_site_url(
        "https://m.instagram.com/reel/Cexample456"
    ) == SiteRoute("instagram", "official-media", None, None)
    assert classify_site_url(
        "https://www.threads.net/@openai/post/Cexample789"
    ) == SiteRoute("threads", "official-post", None, None)
    assert classify_site_url(
        "https://mobile.x.com/openai/status/123456"
    ) == SiteRoute("twitter", "official-post", None, None)
    assert classify_site_url(
        "https://twitter.com/i/web/status/123456"
    ) == SiteRoute("twitter", "official-post", None, None)


def test_social_routes_reject_noncanonical_or_credential_urls() -> None:
    for value in (
        "https://instagram.com/reel/abc",
        "https://threads.com/@openai/post/abc?utm_source=share",
        "https://x.com/openai/status/not-digits",
        "https://x.com.evil.example/openai/status/123456",
        "https://user:secret@www.instagram.com/reel/Cexample456",
    ):
        assert classify_site_url(value) is None
