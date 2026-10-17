"""Presentation-only translations. Backend messages remain stable across languages.

Chinese source messages are catalog keys (including explicit dynamic templates).
Each window owns a translator, so changing language never changes worker state.
"""
import re
from string import Formatter

LANGUAGES = {'zh-CN': '简体中文', 'en': 'English', 'tr': 'Türkçe'}

# source | English | Türkçe; keep both translations together for review.
_ROWS = r'''
CodexPet · 码伴|CodexPet|CodexPet
显示桌宠|Show pet|Evcil hayvanı göster
一键连接 Codex…|Connect to Codex…|Codex’e bağlan…
刷新额度|Refresh usage|Kotayı yenile
切换形象|Appearance|Görünüm
白龙 · 轻晃|White dragon · gentle sway|Beyaz ejderha · hafif sallanma
圆脸 Q 版 · 挤压回弹|Chibi · squash and stretch|Chibi · sıkışıp esneme
始终置顶|Always on top|Her zaman üstte
轻微呼吸动画|Idle breathing animation|Hafif nefes animasyonu
桌宠大小|Pet size|Karakter boyutu
移回屏幕右下角|Move to bottom right|Sağ alt köşeye taşı
选择 codex.exe…|Choose codex.exe…|codex.exe seç…
连接帮助|Connection help|Bağlantı yardımı
重置卡与积分说明|About reset cards and credits|Sıfırlama kartları ve krediler
打开项目文件夹|Open project folder|Proje klasörünü aç
隐藏到托盘|Hide to system tray|Sistem tepsisine gizle
退出码伴|Quit CodexPet|CodexPet’ten çık
选择 Codex CLI 的 codex.exe|Choose the Codex CLI executable|Codex CLI uygulamasını seç
演示数据|Demo data|Örnek veri
读取中|Loading|Yükleniyor
旧数据|Outdated|Eski veri
未连接|Offline|Bağlı değil
待刷新|Refresh due|Yenile
已同步|Synced|Güncel
等待连接|Waiting|Bekliyor
主要额度|Primary limit|Birincil kota
次要额度|Secondary limit|İkincil kota
额度窗口|Usage limit|Kota aralığı
每周额度|Weekly limit|Haftalık kota
{count} 天额度|{count}-day limit|{count} günlük kota
{count} 小时额度|{count}-hour limit|{count} saatlik kota
{count} 分钟额度|{count}-minute limit|{count} dakikalık kota
上次|Previous|Önceki
剩余|Left|Kalan
重置卡|Reset cards|Sıfırlama kartı
额外积分|Extra credits|Ek kredi
未提供|Unavailable|Veri yok
不限量|Unlimited|Sınırsız
{count} 张|{count}|{count}
{label} · 上次|{label} · old|{label} · eski
连接异常 · 点击一键连接|Connection issue · click to connect|Bağlantı sorunu · bağlanmak için tıkla
上次数据 · 等待同步|Previous data · waiting to sync|Önceki veri · eşitleme bekleniyor
收起详情|Hide details|Ayrıntıları gizle
点击查看重置时间|Click for reset times|Sıfırlama zamanları için tıkla
重置时间暂不可用|Reset time unavailable|Sıfırlama zamanı yok
已到重置时间，等待刷新|Reset due · waiting for refresh|Sıfırlama zamanı · yenileme bekleniyor
{days} 天 {hours} 小时后重置|Resets in {days}d {hours}h|{days} gün {hours} sa. sonra sıfırlanır
{hours} 小时 {minutes} 分钟后重置|Resets in {hours}h {minutes}m|{hours} sa. {minutes} dk. sonra sıfırlanır
{minutes} 分钟后重置|Resets in {minutes}m|{minutes} dk. sonra sıfırlanır
不到 1 分钟后重置|Resets in less than 1m|1 dk. içinde sıfırlanır
{label} · {date}（本机时间）|{label} · {date} (local)|{label} · {date} (yerel)
{plan} · 上次更新 {stamp}\n每 2 分钟自动刷新 · 右键可调整桌宠|{plan} · Updated {stamp}\nRefreshes every 2 min · right-click for options|{plan} · Güncelleme: {stamp}\n2 dk.da bir yenilenir · seçenekler: sağ tık
{error}；旧数据可能属于此前登录账号。|{error} Previous data may belong to another account.|{error} Önceki veri başka bir hesaba ait olabilir.
正在连接本机 Codex CLI…|Connecting to the local Codex CLI…|Yerel Codex CLI’a bağlanılıyor…
若未登录，请先在终端运行 codex login|If signed out, run codex login in a terminal.|Oturum kapalıysa terminalde codex login çalıştırın.
{label}：剩余 {value}%|{label}: {value}% left|{label}: %{value} kaldı
重置卡：{value}|Reset cards: {value}|Sıfırlama kartı: {value}
额外积分：{value}|Extra credits: {value}|Ek kredi: {value}
暂未同步；点击查看详情|Not synced; click for details|Eşitlenmedi; ayrıntılar için tıklayın
嗯…再摸一下也可以。|Mm… one more head pat?|Hmm… bir kez daha okşar mısın?
摸摸头，今天也辛苦啦。|A head pat after a long day ♡|Yorucu bir günün ardından ♡
我会帮你看着额度的。|I’ll keep an eye on your usage.|Kotanı senin için takip ederim.
收到你的摸摸啦 ♡|Head pat received ♡|Okşamanı hissettim ♡
按住拖动，就能带我换个位置。|Hold and drag to move me.|Beni taşımak için tutup sürükle.
形象素材缺失，请保留完整的软件文件夹|Missing image; keep the full app folder.|Görsel eksik; uygulama klasörünü koruyun.
正在读取，稍后再更换路径|Reading… change the path shortly.|Okunuyor… yolu birazdan değiştirin.
连接好了，我来帮你看着额度。|Connected! I’ll watch your usage.|Bağlandım! Kotanı takip edeceğim.
正在关闭连接…|Closing connection…|Bağlantı kapatılıyor…
连接 Codex · 码伴|Connect to Codex|Codex’e bağlan
让码伴帮你看着额度|Let CodexPet watch your usage|Kotanızı CodexPet takip etsin
自动检测 Codex 并复用已有登录。\n缺少 CLI 时会下载 OpenAI 官方版本；未登录时打开浏览器授权。|Detects Codex and uses your existing sign-in.\nIf needed, downloads the official OpenAI CLI and opens your browser to sign in.|Codex’i bulur ve mevcut oturumunuzu kullanır.\nGerekirse resmi OpenAI CLI’ını indirir ve giriş için tarayıcıyı açar.
准备好后，点击下方按钮开始。|Click Connect when you’re ready.|Hazır olduğunuzda Bağlan’a tıklayın.
无需填写 API Key。密码和验证码只在官方登录页面输入。\n请与 Codex 桌面应用使用同一账号；重新登录会更新 CLI 登录。|No API key needed. Enter passwords and verification codes only on the official sign-in page.\nUse the same account as the Codex desktop app. Signing in again updates the CLI account.|API anahtarı gerekmez. Şifre ve doğrulama kodlarını yalnızca resmi giriş sayfasına girin.\nCodex masaüstü uygulamasıyla aynı hesabı kullanın. Yeniden giriş, CLI hesabını günceller.
一键连接 Codex|Connect|Bağlan
关闭|Close|Kapat
重新登录|Sign in again|Yeniden giriş
取消连接|Cancel|İptal
连接成功！额度、重置卡和额外积分已同步。\n以后打开码伴会自动连接。|Connected! Usage, reset cards and extra credits are synced.\nCodexPet will connect automatically next time.|Bağlandı! Kota, sıfırlama kartları ve ek krediler eşitlendi.\nCodexPet bir sonraki açılışta otomatik bağlanacak.
重新检测|Check again|Tekrar denetle
使用 ChatGPT 登录|Sign in with ChatGPT|ChatGPT ile giriş yap
重试连接|Retry|Tekrar dene
正在取消连接…|Cancelling connection…|Bağlantı iptal ediliyor…
连接已取消，可以随时重试。|Connection cancelled. You can try again anytime.|Bağlantı iptal edildi. İstediğiniz zaman tekrar deneyebilirsiniz.
连接未完成，请重试或手动选择已安装的 codex.exe。|Could not connect. Retry or choose an installed codex.exe.|Bağlanılamadı. Tekrar deneyin veya kurulu codex.exe dosyasını seçin.
本次连接成功，但无法保存配置。请将软件移动到可写目录，以便下次自动连接。|Connected, but settings could not be saved. Move the app to a writable folder to connect automatically next time.|Bağlandı ancak ayarlar kaydedilemedi. Sonraki açılışta otomatik bağlanmak için uygulamayı yazılabilir bir klasöre taşıyın.
读取遇到异常，请检查 CLI 后刷新重试|Read failed. Check the CLI and refresh.|Okuma başarısız. CLI’ı kontrol edip yenileyin.
设置中的 codex.exe 路径不可用，请右键重新选择|Saved codex.exe path is unavailable. Right-click to choose it again.|Kayıtlı codex.exe yolu kullanılamıyor. Sağ tıklayıp yeniden seçin.
未找到 Codex CLI：请安装并登录，或右键选择 codex.exe|Codex CLI not found. Install and sign in, or right-click to choose codex.exe.|Codex CLI bulunamadı. Kurup giriş yapın veya sağ tıklayıp codex.exe seçin.
登录状态不可用：请在终端运行 codex login，再点击刷新|Sign-in unavailable. Run codex login in a terminal, then refresh.|Oturum kullanılamıyor. Terminalde codex login çalıştırıp yenileyin.
暂时无法连接 Codex 服务，请检查网络后刷新|Cannot reach Codex. Check your network and refresh.|Codex’e ulaşılamıyor. Ağınızı kontrol edip yenileyin.
Codex 未能返回额度，请检查 CLI 登录状态或更新 CLI|Codex returned no usage data. Check CLI sign-in or update the CLI.|Codex kota verisi döndürmedi. CLI oturumunu kontrol edin veya CLI’ı güncelleyin.
无法启动 Codex CLI，请检查 codex.exe 路径|Cannot start Codex CLI. Check the codex.exe path.|Codex CLI başlatılamıyor. codex.exe yolunu kontrol edin.
Codex 连接已中断，请刷新重试|Codex connection interrupted. Refresh to retry.|Codex bağlantısı kesildi. Yenileyip tekrar deneyin.
Codex 服务未能启动，请检查 CLI 配置与登录状态|Codex could not start. Check CLI settings and sign-in.|Codex başlatılamadı. CLI ayarlarını ve oturumu kontrol edin.
Codex 连接已关闭，请刷新重试|Codex connection closed. Refresh to retry.|Codex bağlantısı kapandı. Yenileyip tekrar deneyin.
读取额度超时，稍后会自动重试|Usage read timed out. Retrying automatically later.|Kota okuma zaman aşımı. Daha sonra otomatik denenecek.
未能确认登录状态，请更新 Codex CLI 后重试|Cannot confirm sign-in. Update Codex CLI and retry.|Oturum doğrulanamadı. Codex CLI’ı güncelleyip tekrar deneyin.
登录状态格式不受支持，请更新 Codex CLI 后重试|Unsupported sign-in response. Update Codex CLI and retry.|Oturum yanıtı desteklenmiyor. Codex CLI’ı güncelleyip tekrar deneyin.
已取消|Cancelled|İptal edildi
连接已取消|Connection cancelled|Bağlantı iptal edildi
没有收到有效的额度数据|No valid usage data received.|Geçerli kota verisi alınamadı.
当前账号未返回 Codex 额度，请确认 CLI 使用 ChatGPT 账号登录|No Codex usage returned. Sign in to the CLI with a ChatGPT account.|Codex kotası döndürülmedi. CLI’a ChatGPT hesabıyla giriş yapın.
当前账号未提供可显示的额度；请确认使用 ChatGPT 账号登录|No usage available. Make sure you signed in with a ChatGPT account.|Kota verisi yok. ChatGPT hesabıyla giriş yaptığınızdan emin olun.
官方安装包地址校验失败|Official package URL validation failed.|Resmi paket adresi doğrulanamadı.
官方安装包下载地址不受支持|Unsupported official package download URL.|Resmi paket indirme adresi desteklenmiyor.
自动安装支持 Windows x64 和 ARM64，请手动选择 codex.exe|Auto-install supports Windows x64 and ARM64. Choose codex.exe manually.|Otomatik kurulum Windows x64 ve ARM64’ü destekler. codex.exe dosyasını elle seçin.
官方版本信息无效，请稍后重试|Invalid official release information. Try again later.|Resmi sürüm bilgisi geçersiz. Daha sonra tekrar deneyin.
官方版本没有提供此系统的安装包|No official package available for this system.|Bu sistem için resmi paket bulunamadı.
官方安装包来源校验失败|Official package source validation failed.|Resmi paket kaynağı doğrulanamadı.
官方安装包暂未提供校验值，请稍后重试或手动安装 CLI|No package checksum available. Retry later or install the CLI manually.|Paket sağlama değeri yok. Daha sonra deneyin veya CLI’ı elle kurun.
下载校验失败，请重试；未安装该文件|Download verification failed; nothing installed. Retry.|İndirme doğrulanamadı; dosya kurulmadı. Tekrar deneyin.
官方安装包内容不受支持，请手动安装 CLI|Unsupported package contents. Install the CLI manually.|Paket içeriği desteklenmiyor. CLI’ı elle kurun.
正在获取 OpenAI 官方 CLI 安装信息…|Fetching official OpenAI CLI release information…|Resmi OpenAI CLI sürüm bilgisi alınıyor…
下载超过大小或时间限制，请检查网络后重试|Download size or time limit exceeded. Check your network and retry.|İndirme boyutu veya süre sınırı aşıldı. Ağınızı kontrol edip tekrar deneyin.
正在下载 {program}：{mb} MB（首次连接需要）|Downloading {program}: {mb} MB (first-time setup)|{program} indiriliyor: {mb} MB (ilk kurulum)
正在校验并准备 {program}…|Verifying and preparing {program}…|{program} doğrulanıp hazırlanıyor…
自动安装未完成，请检查网络后重试，或在菜单中手动选择 codex.exe|Auto-install failed. Check your network and retry, or choose codex.exe from the menu.|Otomatik kurulum başarısız. Ağınızı kontrol edip deneyin veya menüden codex.exe seçin.
无法启动官方登录，请重试或手动运行 codex login|Cannot start official sign-in. Retry or run codex login manually.|Resmi giriş başlatılamadı. Tekrar deneyin veya codex login çalıştırın.
登录等待超时，请重试并在浏览器中完成授权|Sign-in timed out. Retry and finish authorization in your browser.|Giriş zaman aşımına uğradı. Tekrar deneyip tarayıcıda yetkilendirmeyi tamamlayın.
登录未完成。请重试；若浏览器未打开，可手动运行 codex login|Sign-in incomplete. Retry; if the browser did not open, run codex login manually.|Giriş tamamlanmadı. Tekrar deneyin; tarayıcı açılmazsa codex login çalıştırın.
正在检测本机 Codex…|Detecting local Codex…|Yerel Codex aranıyor…
正在检查登录状态…|Checking sign-in status…|Oturum durumu denetleniyor…
当前 CLI 使用其他登录方式。点击“使用 ChatGPT 登录”将切换 CLI 登录，以读取套餐额度。|The CLI uses another sign-in method. Choose “Sign in with ChatGPT” to switch accounts and read plan usage.|CLI başka bir giriş yöntemi kullanıyor. Paket kotasını okumak için “ChatGPT ile giriş yap” ile CLI oturumunu değiştirin.
请在浏览器完成 ChatGPT 登录，完成后这里会自动连接。最多等待 5 分钟。|Sign in to ChatGPT in your browser. Connection resumes automatically; waiting up to 5 minutes.|Tarayıcıda ChatGPT’ye giriş yapın. Bağlantı otomatik devam eder; en fazla 5 dakika beklenir.
未检测到 ChatGPT 登录，请重试或检查 CLI 的登录配置|ChatGPT sign-in not found. Retry or check CLI sign-in settings.|ChatGPT oturumu bulunamadı. Tekrar deneyin veya CLI giriş ayarlarını kontrol edin.
正在验证额度连接…|Verifying usage connection…|Kota bağlantısı doğrulanıyor…
重置卡与额外积分 · 码伴|Reset cards and extra credits|Sıfırlama kartları ve ek krediler
重置卡：每次兑换消耗 1 张，用于重置符合条件的 Codex 额度窗口。|Reset cards: redeeming one card resets eligible Codex usage windows.|Sıfırlama kartları: bir kart kullanmak uygun Codex kota aralıklarını sıfırlar.
具体恢复哪些窗口以 Codex 的兑换说明和结果为准；卡片可能有到期时间。|Check Codex’s redemption instructions and result for eligible windows. Cards may expire.|Uygun aralıklar için Codex’in kullanım açıklamalarına ve sonucuna bakın. Kartların süresi dolabilir.
需要兑换时，请在 Codex 中使用重置入口。码伴只显示数量。|Redeem cards in Codex. CodexPet only displays the count.|Kartları Codex’te kullanın. CodexPet yalnızca sayıyı gösterir.
额外积分：套餐额度用尽后可继续使用的 credits 余额，不是金额或消息条数。|Extra credits: credits available after your plan limit is reached; not money or message counts.|Ek krediler: paket kotası dolduğunda kullanılabilen kredi bakiyesidir; para veya mesaj sayısı değildir.
余额按两位小数显示；“不限量”仅在服务明确返回时显示。|Balances show two decimal places. “Unlimited” appears only when explicitly returned by the service.|Bakiye iki ondalık basamakla gösterilir. “Sınırsız” yalnızca hizmet açıkça bildirdiğinde görünür.
两项与额度每 2 分钟一起刷新；“未提供”表示 CLI 或服务没有返回数据。|Both refresh with usage every 2 minutes. “Unavailable” means the CLI or service returned no data.|Her ikisi kotayla birlikte 2 dakikada bir yenilenir. “Veri yok”, CLI veya hizmetin veri döndürmediğini belirtir.
连接失败时保留上次结果并标记“上次”，不会把未知数据当成 0。|Failed connections retain previous results marked as old. Unknown values are never treated as zero.|Bağlantı hatalarında önceki sonuçlar eski olarak işaretlenir. Bilinmeyen değerler sıfır sayılmaz.
码伴读取本机 Codex CLI 当前登录账号的额度。|CodexPet reads usage for the account signed in to the local Codex CLI.|CodexPet, yerel Codex CLI’da oturum açmış hesabın kotasını okur.
推荐：右键选择“一键连接 Codex”，自动检测、安装并引导登录。|Right-click → Connect to Codex to detect, install and sign in automatically.|Otomatik algılama, kurulum ve giriş için sağ tık → Codex’e bağlan seçeneğini kullanın.
若浏览器未打开，可在终端手动运行 codex login。|If the browser does not open, run codex login in a terminal.|Tarayıcı açılmazsa terminalde codex login çalıştırın.
完成后点击刷新，或在连接窗口中重试。|Then refresh or retry in the connection window.|Ardından yenileyin veya bağlantı penceresinde tekrar deneyin.
CLI 账号可能与 Codex 桌面应用中的账号不同，请使用同一个账号。|The CLI account may differ from the Codex desktop app. Use the same account in both.|CLI hesabı Codex masaüstü uygulamasındakinden farklı olabilir. İkisinde de aynı hesabı kullanın.
也可以右键“选择 codex.exe”指定已安装的原生 CLI。|You can also right-click → Choose codex.exe to select an installed native CLI.|Kurulu yerel CLI’ı seçmek için sağ tık → codex.exe seç seçeneğini de kullanabilirsiniz.
两条额度来自服务返回的窗口；缺失数据会显示 —。|Both limits use the windows returned by the service. Missing data shows —.|İki kota da hizmetin döndürdüğü aralıklardır. Eksik veri — olarak gösterilir.
刷新只查询额度；摸头和动画由本地程序完成。|Refresh only reads usage. Head pats and animations run locally.|Yenileme yalnızca kotayı sorgular. Okşama ve animasyonlar yerel olarak çalışır.
'''

CATALOG = {}
_PATTERNS = []
for row in _ROWS.strip().splitlines():
    source, en, tr = (part.replace(r'\n', '\n') for part in row.split('|'))
    CATALOG[source] = {'en': en, 'tr': tr}
    if '{' in source:
        pattern = ''.join(re.escape(literal) + (f'(?P<{field}>.+?)' if field else '')
                          for literal, field, _, _ in Formatter().parse(source))
        _PATTERNS.append((re.compile(pattern), source))


class Translator:
    def __init__(self, language='zh-CN'):
        self.language = language if isinstance(language, str) and language in LANGUAGES else 'zh-CN'

    def __call__(self, source):
        if self.language == 'zh-CN' or not source:
            return source
        if source in CATALOG:
            return CATALOG[source][self.language]
        for pattern, key in _PATTERNS:
            match = pattern.fullmatch(source)
            if match:
                return CATALOG[key][self.language].format(**{k: self(v) for k, v in match.groupdict().items()})
        if '\n' in source:
            return '\n'.join(self(line) for line in source.split('\n'))
        return source

    def number(self, value):
        """Localize a formatted number once, without touching paths or dates."""
        return value.translate(str.maketrans(',.', '.,')) if self.language == 'tr' else value
