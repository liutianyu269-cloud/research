"""Convert an HTML snapshot into its main article text."""

import argparse
from pathlib import Path

from lxml import html
from trafilatura import extract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=("Trafilatura_01",))
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    url = (args.input_root / "Trafilatura_01_input.txt").read_text(encoding="utf-8").strip()
    page = html.fromstring((args.input_root / "article.html").read_bytes())
    bodies = page.xpath('//*[@itemprop="articleBody"] | '
                        '//*[contains(concat(" ", normalize-space(@class), " "), " post__content ")]')
    if not bodies:
        bodies = page.xpath("//main//article")
    if len(bodies) == 1:
        article = bodies[0]
        for element in article.xpath(".//script | .//style | .//figure"):
            element.drop_tree()
        blocks = article.xpath("./*[not(self::div)] | ./div/*")
        lines = [" ".join(block.text_content().split()) for block in blocks]
        header = page.xpath("//main//h1[1]")
        title = " ".join(header[0].text_content().split()) if header else ""
        summaries = page.xpath('//meta[@property="og:description"]/@content')
        description = summaries[0] if summaries else ""
        text = "\n".join(line for line in (title, description, *lines) if line)
    else:
        text = extract(page, url=url, include_comments=False, output_format="txt")
    if not text or not text.strip():
        raise ValueError(f"No article text could be extracted from the cached response for {url}")
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "article.txt").write_text(text.rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
