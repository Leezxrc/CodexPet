# CodexPet

Codex kotasını, sıfırlama kartlarını ve ek kredileri gösteren bir Windows masaüstü arkadaşı. İki görünüm, baş okşama, sürükleme, sistem tepsisi menüsü ve tek tıkla bağlantı içerir.

1. [Windows sürümünü](https://github.com/Leezxrc/CodexPet/releases/latest) indirip tamamen çıkarın veya deponun tamamını klonlayın.
2. `app/CodexPet/CodexPet.exe` dosyasını açın. Yanındaki `_internal` klasörünü koruyun. Python gerekmez.
3. Karaktere sağ tıklayın → **语言 / Language / Dil** → **Türkçe**. Seçiminiz hemen uygulanır ve kaydedilir.
4. **Codex’e bağlan…** → **Bağlan** seçeneğini kullanın. Mevcut CLI oturumu kullanılır; gerekirse resmi CLI indirilir ve giriş için tarayıcı açılır. Codex masaüstü uygulamasıyla aynı ChatGPT hesabını kullanın.

Tepki almak için karakterin başına tıklayın. Chibi’nin ayakları sabit kalırken gövdesi aşağı doğru sıkışır ve yanlara genişler. Taşımak için sürükleyin; sıfırlama zamanları için kota kartına tıklayın. Görünüm, boyut ve animasyon sağ tık menüsünden değiştirilebilir. Kota iki dakikada bir yenilenir. Eksik veri sıfır olarak gösterilmez; yenileme başarısız olursa önceki veri eski olarak işaretlenir. Ek kredi, para veya mesaj sayısı değildir. Sıfırlama kartlarını Codex içinde kullanın; bu uygulama yalnızca sayısını gösterir.

Başlat menüsüne kısayol eklemek için proje klasöründe `powershell -ExecutionPolicy Bypass -File tools\install-start-menu.ps1` çalıştırın. Kısayolun adı **CodexPet · 码伴** olacaktır. Klasörü taşırsanız komutu yeniden çalıştırın. Ayarlar ve indirilen CLI dosyaları yerel `data/` klasöründe (proje salt okunursa `%LOCALAPPDATA%/CodexPet` altında) tutulur ve GitHub’a yüklenmez.

Kapalı uygulamayı `CodexPet.exe --language tr` ile de başlatabilirsiniz. Uygulama zaten açıksa dil menüsünü kullanın. Okşama ve animasyonlar model çağrısı yapmaz. Türkçe arayüzde ondalık ayırıcı virgüldür.

![Örnek verilerle Türkçe arayüz](preview-tr.png)

![Bağlantı kurulumu](preview-connection-tr.png)
