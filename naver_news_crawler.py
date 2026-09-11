import argparse
import re
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement
from urllib.parse import quote

from openpyxl import Workbook
import requests
from bs4 import BeautifulSoup


SEARCH_URL = "https://search.naver.com/search.naver?where=nexearch&query={}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
}


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def is_article_url(url):
    return (
        "/article/" in url
        or "/mnews/article/" in url
        or "/view/" in url
        or "news.naver.com" in url
    )


def get_soup(session, url):
    response = session.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def search_news(session, query, limit=10):
    soup = get_soup(session, SEARCH_URL.format(quote(query)))
    articles = []
    seen_urls = set()

    title_links = soup.select("a.news_tit")
    if not title_links:
        title_links = soup.select("div.fds-news-item-list-desk a[href]")

    for link in title_links:
        title = clean_text(link.get_text(" ", strip=True))
        url = link.get("href", "").strip()

        if not title or not url.startswith("http") or not is_article_url(url):
            continue
        if title.endswith("새 창 열림"):
            title = clean_text(title.removesuffix("새 창 열림"))
        if (
            not title
            or title == "네이버뉴스"
            or "ader.naver.com" in url
            or "media.naver.com/press/" in url
        ):
            continue
        if url in seen_urls:
            continue

        seen_urls.add(url)
        articles.append({"title": title, "url": url})
        if len(articles) >= limit:
            break

    return articles


def extract_article_content(session, article_url):
    soup = get_soup(session, article_url)

    for selector in (
        "#dic_area",
        "#newsct_article",
        "#articleBodyContents",
        "div.article_body",
        "article",
    ):
        article = soup.select_one(selector)
        if article:
            for unwanted in article.select("script, style, iframe, aside"):
                unwanted.decompose()
            content = clean_text(article.get_text(" ", strip=True))
            if content:
                return content

    return "본문을 찾지 못했습니다. 해당 언론사의 HTML 구조를 확인하세요."


def crawl_news(query, limit=10):
    with requests.Session() as session:
        articles = search_news(session, query, limit)
        for article in articles:
            try:
                article["content"] = extract_article_content(session, article["url"])
            except requests.RequestException as error:
                article["content"] = f"본문 요청 실패: {error}"
        return articles


def save_articles_to_xml(articles, file_path="naver_news_crawler.xml"):
    root = Element("news", {"count": str(len(articles))})

    for article in articles:
        article_element = SubElement(root, "article")
        SubElement(article_element, "title").text = article["title"]
        SubElement(article_element, "url").text = article["url"]
        SubElement(article_element, "content").text = article.get("content", "")

    ElementTree(root).write(file_path, encoding="utf-8", xml_declaration=True)


def save_articles_to_xlsx(articles, file_path="naver_news_crawler.xlsx"):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Naver News"
    worksheet.append(["번호", "제목", "링크", "본문"])

    for number, article in enumerate(articles, start=1):
        worksheet.append(
            [
                number,
                article["title"],
                article["url"],
                article.get("content", ""),
            ]
        )

    worksheet.freeze_panes = "A2"
    worksheet.column_dimensions["A"].width = 8
    worksheet.column_dimensions["B"].width = 50
    worksheet.column_dimensions["C"].width = 70
    worksheet.column_dimensions["D"].width = 100
    workbook.save(file_path)


def main():
    parser = argparse.ArgumentParser(description="네이버 뉴스 검색 결과와 기사 본문 크롤러")
    parser.add_argument("query", nargs="?", default="반도체", help="검색어")
    parser.add_argument("--limit", type=int, default=5, help="수집할 기사 수")
    parser.add_argument(
        "--xlsx",
        action="store_true",
        help="XML과 함께 openpyxl 형식의 XLSX 파일도 저장",
    )
    args = parser.parse_args()

    articles = crawl_news(args.query, args.limit)
    save_articles_to_xml(articles)
    if args.xlsx:
        save_articles_to_xlsx(articles)

    print(f"{len(articles)}건을 {Path('naver_news_crawler.xml').resolve()}에 저장했습니다.")
    for number, article in enumerate(articles, start=1):
        print(f"\n[{number}] {article['title']}")
        print(f"링크: {article['url']}")
        print(f"본문: {article['content'][:500]}...")


if __name__ == "__main__":
    main()