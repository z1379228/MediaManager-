"""Trusted, read-only feature introduction for the desktop UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeatureIntroductionSection:
    """One user-facing feature group and the caveats required to use it safely."""

    section_id: str
    title: str
    category: str
    summary: str
    notes: tuple[str, ...]


FEATURE_INTRODUCTION_SECTIONS = (
    FeatureIntroductionSection(
        "download-search",
        "下載與網站搜尋",
        "核心／內建 MOD",
        "集中處理 YouTube、YouTube Music、Bilibili 與已驗證白名單網站的公開內容。",
        (
            "支援手動網址、公開搜尋、播放清單／批次工作，以及 YouTube 相似音樂候選。",
            "Bilibili 使用獨立工作區，可處理番劇、分 P 與選用的 XML／ASS／MKV 彈幕流程。",
            "網站介面變動、來源限制或外部解析工具失效時，個別功能可能暫時不可用。",
        ),
    ),
    FeatureIntroductionSection(
        "download-inbox",
        "下載收件匣與工作佇列",
        "核心",
        "先檢查手動網址或 TXT／CSV，再由使用者確認格式並加入可追蹤的工作佇列。",
        (
            "支援限制併發、暫停、取消、重試、歷史與啟動後恢復；乾淨啟動不會自行開始新下載。",
            "網址辨識、標題與縮圖只供確認，不代表來源一定可下載或允許使用。",
            "取消與失敗可能留下明確標示的暫存檔；完成檔案不會因移除佇列項目而自動刪除。",
        ),
    ),
    FeatureIntroductionSection(
        "other-sources",
        "其他來源與官方工具",
        "內建 MOD",
        "MEGA、Direct HTTP、Facebook 與官方社群頁面各自維持獨立邊界。",
        (
            "MEGA 只辨識公開分享，實際下載需使用者另行安裝官方 MEGAcmd。",
            "Direct HTTP 只接收明確的公開 HTTPS 檔案網址，並提供續傳與雜湊驗證。",
            "Facebook 只處理使用者提供的公開影片網址；Instagram、Threads 與 X 工作區只開啟官方頁面或官方資料匯出，不是下載器。",
        ),
    ),
    FeatureIntroductionSection(
        "podcast-rss",
        "Podcast / RSS 本機匯入",
        "內建 MOD",
        "讀取使用者選取的本機 RSS 2.0／Atom 檔案，預覽單集、逐字稿與章節資訊。",
        (
            "只讀取最大 2 MiB 的本機 .rss、.xml 或 .atom；不訂閱、不刷新，也不向 Feed 內網址連線。",
            "為避免 XML 外部實體、記憶體與介面資源風險，拒絕 DTD／實體宣告、過深結構及超過 500 集的檔案。",
            "只有符合 Direct HTTP 明確 HTTPS 檔案規則的附件可手動交接；交接只預填欄位，不會自動分析、排隊或下載。",
            "逐字稿與 Podcasting 2.0 章節目前只顯示可用狀態，不會在背景下載內容。",
        ),
    ),
    FeatureIntroductionSection(
        "peertube-search",
        "PeerTube 節點搜尋",
        "內建搜尋 MOD",
        "搜尋使用者明確指定之公開 PeerTube 實例中的本機公開影片。",
        (
            "每次需輸入 HTTPS 實例根網址；不保存登入、Cookie、Token 或節點清單。",
            "只使用官方公開搜尋 API、local 搜尋目標與本機影片篩選，不查第三方搜尋索引，也不以影片網址觸發遠端物件擷取。",
            "實例網址會先拒絕私有、回環與其他非公開 DNS 位址，API 重新導向也不會跟隨。",
            "結果只提供明確的系統瀏覽器開啟動作；目前不解析串流、不預覽縮圖，也不自動交給下載器。",
        ),
    ),
    FeatureIntroductionSection(
        "library",
        "本機媒體庫",
        "核心",
        "掃描使用者選取的本機資料夾，建立可搜尋的 SQLite 媒體索引與播放清單。",
        (
            "完整重複確認會比對 SHA-256，流程可取消且不會自動刪除來源檔案。",
            "編輯標題、歌手、標籤或套用 MusicBrainz 預覽時只更新媒體庫資料，不改寫媒體檔。",
            "來源檔案移動、離線或在驗證期間變更時會保守地標示或拒絕操作。",
        ),
    ),
    FeatureIntroductionSection(
        "format-factory",
        "格式工廠",
        "內建 MOD",
        "使用本機 FFmpeg 進行影音、音訊、影像、字幕、切割、串接、壓縮與浮水印處理。",
        (
            "原始檔預設保留，工作先寫入暫存檔，成功後才建立新輸出檔。",
            "GPU 編碼器是否可用取決於顯示卡、驅動與本機 FFmpeg；不可用時只在預設允許的方案回退 CPU。",
            "音訊或字幕串流複製只有在來源編碼與輸出容器相容時可用；品質、容量與速度無法同時無條件最大化。",
            "本機廣告段落剪除只依使用者手動指定的時間區間工作，不偵測或繞過網站廣告。",
        ),
    ),
    FeatureIntroductionSection(
        "gopeed-p2p",
        "Gopeed Bridge／P2P Transfer",
        "內建 MOD",
        "把明確的 HTTPS、magnet 或 ed2k 工作交給使用者自行啟動的 localhost Gopeed。",
        (
            "MediaManager 不會啟動或設定 Gopeed、不開啟路由器連接埠，也不把 API Token 寫入設定檔。",
            "P2P 必須明確確認合法用途；上傳與持續做種另需確認並設定正數上傳上限。",
            "移除 MediaManager 內的工作不等於刪除已下載檔案；外部 Gopeed 工作也不會被隱含取消。",
        ),
    ),
    FeatureIntroductionSection(
        "speech-to-text",
        "Speech to Text",
        "選用 MOD／預設關閉",
        "以本機 whisper-cli 與使用者匯入的模型輸出 TXT、SRT 或 VTT。",
        (
            "需完整 whisper.cpp Windows 執行環境（EXE 與相鄰 DLL）及經 SHA-256 驗證的模型；程式不會自行下載模型。",
            "模型大小會直接影響記憶體、速度與辨識品質；大型模型不一定適合低記憶體電腦。",
            "VAD 只有在本機 whisper-cli 支援對應參數且模型驗證通過後才能手動啟用。",
        ),
    ),
    FeatureIntroductionSection(
        "automation",
        "Automation",
        "選用 MOD／預設關閉",
        "提供排程網址、資料夾監看與剪貼簿網址候選，規則必須由使用者逐項啟用。",
        (
            "自動化只派送至已啟用且可用的工作區，不會替使用者略過格式與安全檢查。",
            "資料夾監看與短週期排程會增加磁碟或 CPU 使用量；背景待機會降低非必要喚醒頻率。",
            "停用 MOD、退出程式或取消規則會停止後續派送，不會秘密維持另一個背景服務。",
        ),
    ),
    FeatureIntroductionSection(
        "background-idle",
        "背景待機、系統匣與開機啟動",
        "核心設定",
        "最小化或關閉至系統匣時暫停不可見介面的非必要更新，保留進行中的工作。",
        (
            "背景待機不是完全結束；下載與已啟用排程仍可繼續，系統匣可重新開啟或完全結束。",
            "右下角可選擇關閉至系統匣或完全結束；系統匣不可用時會安全退回完全結束。",
            "Windows 登入後自動啟動預設關閉，啟用時只建立目前使用者的背景啟動項。",
        ),
    ),
    FeatureIntroductionSection(
        "mods",
        "內建與第三方 MOD",
        "擴充架構",
        "內建功能可個別停用；第三方 MOD 透過版本化契約與受控程序擴充，不直接注入可信 UI。",
        (
            "新的可執行 MOD 使用 manifest schema v2、runtime protocol 1.0 與最小必要 capability。",
            "安裝前驗證套件結構、SHA-256、發布者與 Ed25519 簽章；新安裝或更新後預設停用。",
            "第三方介面只接受受簽署的宣告式 ui.json，不執行 HTML、Qt 物件或任意腳本。",
            "外部 MOD 的可用性、授權、網站條款與技術支援由其作者負責；核心不會為相容而放寬安全界線。",
        ),
    ),
    FeatureIntroductionSection(
        "safety-release",
        "安全、資料與版本界線",
        "使用前必讀",
        "實際可用功能以「執行環境」與「MOD 管理」的目前狀態為準。",
        (
            "不繞過 DRM、登入、Cookie、Cloudflare、廣告、付費、地區或其他網站存取限制。",
            "程式預設本機優先且不遙測；Token、Cookie、私鑰與憑證不得寫入 Repository 或 Log。",
            "Testing 套件可能未經 Authenticode 簽署；只從專案 Release 下載並先核對隨附 SHA-256。",
            "自包含 ZIP 代表免安裝，不等於資料完全可攜；設定與資料位置仍由啟動模式決定。",
        ),
    ),
)


def feature_introduction_search_text(section: FeatureIntroductionSection) -> str:
    """Return normalized searchable text for one presentation section."""

    return " ".join(
        (section.title, section.category, section.summary, *section.notes)
    ).casefold()


def create_feature_introduction_dialog(parent: object = None) -> object:
    """Create the non-mutating, searchable feature introduction dialog."""

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )

    dialog = QDialog(parent)
    dialog.setObjectName("featureIntroductionDialog")
    dialog.setWindowTitle("功能簡介")
    dialog.setAccessibleName("MediaManager 功能簡介")
    dialog.resize(880, 680)
    dialog.setMinimumSize(720, 520)

    page = QVBoxLayout(dialog)
    page.setContentsMargins(20, 18, 20, 16)
    page.setSpacing(12)

    title = QLabel("MediaManager 功能簡介")
    title.setObjectName("sectionTitle")
    page.addWidget(title)

    intro = QLabel(
        "本頁只說明目前功能、必要依賴與操作界線，不會啟用 MOD、下載工具、"
        "連線網站或改變設定。實際狀態請以主畫面的執行環境與 MOD 管理為準。"
    )
    intro.setObjectName("modUsageGuide")
    intro.setAccessibleName("功能簡介使用說明")
    intro.setWordWrap(True)
    intro.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    page.addWidget(intro)

    search_row = QHBoxLayout()
    search = QLineEdit()
    search.setObjectName("featureIntroductionSearch")
    search.setAccessibleName("搜尋功能簡介")
    search.setPlaceholderText("搜尋功能、依賴或注意事項…")
    search.setClearButtonEnabled(True)
    count = QLabel()
    count.setObjectName("muted")
    count.setAccessibleName("功能簡介顯示數量")
    search_row.addWidget(search, 1)
    search_row.addWidget(count)
    page.addLayout(search_row)

    scroll = QScrollArea()
    scroll.setObjectName("featureIntroductionScroll")
    scroll.setAccessibleName("功能簡介內容")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    content = QWidget()
    content.setObjectName("featureIntroductionContent")
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(2, 2, 8, 2)
    content_layout.setSpacing(10)

    cards: list[tuple[QFrame, str]] = []
    for section in FEATURE_INTRODUCTION_SECTIONS:
        card = QFrame()
        card.setObjectName("card")
        card.setProperty("featureIntroductionId", section.section_id)
        card.setAccessibleName(f"{section.title}功能說明")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(7)

        heading = QHBoxLayout()
        section_title = QLabel(section.title)
        section_title.setObjectName("fieldLabel")
        category = QLabel(section.category)
        category.setObjectName("providerBadge")
        category.setAccessibleName(f"功能分類：{section.category}")
        heading.addWidget(section_title)
        heading.addStretch()
        heading.addWidget(category)
        card_layout.addLayout(heading)

        summary = QLabel(section.summary)
        summary.setWordWrap(True)
        summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card_layout.addWidget(summary)

        notes = QLabel("\n".join(f"• {note}" for note in section.notes))
        notes.setObjectName("sectionSubtitle")
        notes.setWordWrap(True)
        notes.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card_layout.addWidget(notes)

        content_layout.addWidget(card)
        cards.append((card, feature_introduction_search_text(section)))

    no_results = QLabel("沒有符合的功能說明。")
    no_results.setObjectName("emptyText")
    no_results.setAccessibleName("功能簡介沒有搜尋結果")
    no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
    no_results.setVisible(False)
    content_layout.addWidget(no_results)
    content_layout.addStretch()
    scroll.setWidget(content)
    page.addWidget(scroll, 1)

    controls = QHBoxLayout()
    controls.addStretch()
    close = QPushButton("關閉")
    close.setObjectName("primary")
    close.setAccessibleName("關閉功能簡介")
    close.clicked.connect(dialog.accept)
    controls.addWidget(close)
    page.addLayout(controls)

    def apply_filter(value: str) -> None:
        query = value.strip().casefold()
        visible = 0
        for card, searchable in cards:
            matched = not query or query in searchable
            card.setVisible(matched)
            visible += int(matched)
        count.setText(f"顯示 {visible}／{len(cards)} 類")
        no_results.setVisible(visible == 0)

    search.textChanged.connect(apply_filter)
    apply_filter("")
    search.setFocus()
    return dialog


def show_feature_introduction(parent: object) -> None:
    """Show the feature introduction modally from the trusted shell."""

    create_feature_introduction_dialog(parent).exec()
