from noticias_api.pipeline.fetch import parse_feed

RSS_WITH_DC_CREATOR = """<?xml version="1.0"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
  <channel>
    <item>
      <title>Nota A</title>
      <link>http://x/a</link>
      <guid>a</guid>
      <dc:creator>Juan Pérez</dc:creator>
    </item>
    <item>
      <title>Nota B</title>
      <link>http://x/b</link>
      <guid>b</guid>
      <dc:creator>Juan Pérez y María López</dc:creator>
    </item>
    <item>
      <title>Nota C</title>
      <link>http://x/c</link>
      <guid>c</guid>
    </item>
  </channel>
</rss>"""


def test_parse_feed_extracts_authors():
    items = parse_feed(RSS_WITH_DC_CREATOR)
    assert len(items) == 3
    assert items[0].authors == ["Juan Pérez"]
    assert items[1].authors == ["Juan Pérez", "María López"]
    assert items[2].authors == []
