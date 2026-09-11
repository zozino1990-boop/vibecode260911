import re
from urllib.parse import quote
from xml.etree.ElementTree import Element, ElementTree, SubElement

from openpyxl import Workbook
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
import requests
from bs4 import BeautifulSoup


NAVER_SEARCH_URL = (
    "https://search.naver.com/search.naver?where=nexearch&sm=top_hty&"
    "fbm=0&ie=utf8&query={}"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
}


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def request_soup(session, url):
    response = session.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def is_article_url(url):
    return (
        "/article/" in url
        or "/mnews/article/" in url
        or "/view/" in url
        or "news.naver.com" in url
    )


def get_link_text(link):
    text = clean_text(link.get_text(" ", strip=True))
    return clean_text(text.removesuffix("새 창 열림"))


def search_news(session, query, limit=10):
    search_url = NAVER_SEARCH_URL.format(quote(query))
    soup = request_soup(session, search_url)
    articles = []
    seen_urls = set()

    # 현재 네이버 뉴스 HTML: nws_all.*.tit / nws_all.*.body
    title_links = soup.select('a[data-nlog-area*=".tit"]')
    if not title_links:
        title_links = soup.select("a.news_tit")

    for title_link in title_links:
        title = get_link_text(title_link)
        article_url = title_link.get("href", "").strip()
        if not title or not article_url.startswith("http"):
            continue
        if not is_article_url(article_url) or article_url in seen_urls:
            continue

        article_block = title_link.find_parent(
            "div", class_=re.compile(r"sds-comps-vertical-layout")
        )
        body_link = (
            article_block.find("a", attrs={"data-nlog-area": re.compile(r"\.body$")})
            if article_block
            else None
        )
        summary = get_link_text(body_link) if body_link else ""
        seen_urls.add(article_url)
        articles.append(
            {
                "title": title,
                "summary": summary,
                "url": article_url,
            }
        )
        if len(articles) >= limit:
            break

    return articles


def extract_article_content(session, article_url):
    soup = request_soup(session, article_url)
    selectors = (
        "#dic_area",
        "#newsct_article",
        "#articleBodyContents",
        "div.article_body",
        "div.article-body",
        "article",
    )

    for selector in selectors:
        article = soup.select_one(selector)
        if not article:
            continue
        for unwanted in article.select("script, style, iframe, aside"):
            unwanted.decompose()
        content = clean_text(article.get_text(" ", strip=True))
        if content:
            return content

    return "본문을 찾지 못했습니다. 해당 언론사의 HTML 구조를 확인하세요."


def crawl_news(query="반도체", limit=5):
    with requests.Session() as session:
        articles = search_news(session, query, limit)
        for article in articles:
            try:
                article["content"] = extract_article_content(session, article["url"])
            except requests.RequestException as error:
                article["content"] = f"본문 요청 실패: {error}"
        return articles


def save_news_to_xml(articles, file_path="naver_new.xml"):
    root = Element("news", {"count": str(len(articles))})

    for article in articles:
        article_element = SubElement(root, "article")
        SubElement(article_element, "title").text = article.get("title", "")
        SubElement(article_element, "summary").text = article.get("summary", "")
        SubElement(article_element, "url").text = article.get("url", "")
        SubElement(article_element, "content").text = article.get("content", "")

    ElementTree(root).write(file_path, encoding="utf-8", xml_declaration=True)


def save_news_to_xlsx(articles, file_path="naver_new.xlsx"):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Naver News"
    worksheet.append(["번호", "제목", "요약", "링크", "본문"])

    for number, article in enumerate(articles, start=1):
        worksheet.append(
            [
                number,
                article.get("title", ""),
                article.get("summary", ""),
                article.get("url", ""),
                article.get("content", ""),
            ]
        )

    worksheet.freeze_panes = "A2"
    worksheet.column_dimensions["A"].width = 8
    worksheet.column_dimensions["B"].width = 50
    worksheet.column_dimensions["C"].width = 80
    worksheet.column_dimensions["D"].width = 70
    worksheet.column_dimensions["E"].width = 100
    workbook.save(file_path)


class CrawlWorker(QObject):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, query, limit):
        super().__init__()
        self.query = query
        self.limit = limit

    def run(self):
        try:
            self.finished.emit(crawl_news(self.query, self.limit))
        except requests.RequestException as error:
            self.failed.emit(f"네트워크 요청에 실패했습니다: {error}")
        except Exception as error:
            self.failed.emit(f"크롤링 중 오류가 발생했습니다: {error}")


class NewsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.articles = []
        self.thread = None
        self.worker = None
        self.setWindowTitle("Naver News Crawler")
        self.resize(1120, 760)
        self.setMinimumSize(860, 600)
        self.build_ui()

    def build_ui(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #f4f7fb; color: #16233b; }
            QLabel#title { color: #14213d; font-size: 27px; font-weight: 800; }
            QLabel#subtitle, QLabel#status { color: #6b7b93; font-size: 12px; }
            QLineEdit, QSpinBox { background: #ffffff; border: 1px solid #d6dfeb;
                border-radius: 8px; padding: 9px 11px; }
            QLineEdit:focus, QSpinBox:focus { border: 2px solid #55b8a6; }
            QPushButton { border: 0; border-radius: 8px; padding: 10px 18px;
                font-weight: 700; background: #14213d; color: #ffffff; }
            QPushButton:hover { background: #263b63; }
            QPushButton:disabled { background: #b7c2d1; }
            QTableWidget, QTextEdit { background: #ffffff; border: 1px solid #dfe6ef;
                border-radius: 10px; }
            QHeaderView::section { background: #eef3f8; border: 0; padding: 9px;
                color: #53647b; font-weight: 700; }
            QTableWidget { gridline-color: #edf1f5; selection-background-color: #dff5ef;
                selection-color: #16233b; }
            """
        )

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Naver News Crawler")
        title.setObjectName("title")
        subtitle = QLabel("검색어를 입력하면 뉴스 제목, 요약, 본문을 수집합니다.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        controls = QHBoxLayout()
        self.query_input = QLineEdit("반도체")
        self.query_input.setPlaceholderText("검색어")
        self.query_input.returnPressed.connect(self.start_crawl)
        self.limit_input = QSpinBox()
        self.limit_input.setRange(1, 30)
        self.limit_input.setValue(5)
        self.limit_input.setSuffix("건")
        self.search_button = QPushButton("뉴스 검색")
        self.search_button.clicked.connect(self.start_crawl)
        self.save_button = QPushButton("Excel 저장")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_excel_as)
        controls.addWidget(QLabel("검색어"))
        controls.addWidget(self.query_input, 1)
        controls.addWidget(QLabel("개수"))
        controls.addWidget(self.limit_input)
        controls.addWidget(self.search_button)
        controls.addWidget(self.save_button)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["제목", "요약", "링크"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 330)
        self.table.setColumnWidth(1, 480)
        self.table.itemSelectionChanged.connect(self.show_selected_article)
        layout.addWidget(self.table, 3)

        detail_label = QLabel("기사 본문")
        detail_label.setStyleSheet("font-weight: 700; color: #53647b;")
        layout.addWidget(detail_label)
        self.content_view = QTextEdit()
        self.content_view.setReadOnly(True)
        self.content_view.setPlaceholderText("목록에서 기사를 선택하면 본문이 표시됩니다.")
        layout.addWidget(self.content_view, 2)

        self.status_label = QLabel("검색어를 입력하고 뉴스 검색을 눌러주세요.")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)
        self.setCentralWidget(central)

    def start_crawl(self):
        query = self.query_input.text().strip()
        if not query:
            QMessageBox.warning(self, "검색어 필요", "검색어를 입력해주세요.")
            return

        self.search_button.setEnabled(False)
        self.status_label.setText("뉴스를 검색하고 본문을 가져오는 중입니다...")
        self.table.setRowCount(0)
        self.content_view.clear()
        self.thread = QThread()
        self.worker = CrawlWorker(query, self.limit_input.value())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.finish_crawl)
        self.worker.failed.connect(self.fail_crawl)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.clear_worker)
        self.thread.start()

    def finish_crawl(self, articles):
        self.articles = articles
        save_news_to_xml(articles)
        save_news_to_xlsx(articles)
        self.table.setRowCount(len(articles))
        for row, article in enumerate(articles):
            self.table.setItem(row, 0, QTableWidgetItem(article["title"]))
            self.table.setItem(row, 1, QTableWidgetItem(article["summary"]))
            self.table.setItem(row, 2, QTableWidgetItem(article["url"]))
        if articles:
            self.table.selectRow(0)
        self.save_button.setEnabled(bool(articles))
        self.search_button.setEnabled(True)
        self.status_label.setText(
            f"{len(articles)}건 수집 완료 | naver_new.xml, naver_new.xlsx 저장 완료"
        )

    def fail_crawl(self, message):
        self.search_button.setEnabled(True)
        self.status_label.setText("크롤링에 실패했습니다.")
        QMessageBox.critical(self, "크롤링 오류", message)

    def save_excel_as(self):
        if not self.articles:
            QMessageBox.information(self, "저장할 결과 없음", "먼저 뉴스를 검색해주세요.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel 파일 저장",
            "naver_news.xlsx",
            "Excel 파일 (*.xlsx)",
        )
        if not file_path:
            return

        try:
            save_news_to_xlsx(self.articles, file_path)
        except Exception as error:
            QMessageBox.critical(self, "저장 오류", f"Excel 저장에 실패했습니다.\n{error}")
            return
        self.status_label.setText(f"Excel 저장 완료: {file_path}")

    def show_selected_article(self):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            self.content_view.setPlainText(self.articles[rows[0].row()].get("content", ""))

    def clear_worker(self):
        self.worker = None
        self.thread = None


def main():
    app = QApplication([])
    window = NewsWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
