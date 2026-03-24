# QuizBlast Multiplayer 🎯

Seyircilerin QR kod ile katılabildiği canlı web quiz oyunu.

## Kurulum

```bash
pip install flask
# (İsteğe bağlı, daha iyi QR kod için)
pip install qrcode[pil]
```

## Çalıştırma

```bash
cd quizblast_web
python3 app.py
```

## Kullanım

### Host (Sunucu / Öğretmen)
1. Tarayıcıda `http://localhost:5000` adresini açın
2. Şifre: `host123`
3. **ODA OLUŞTUR** butonuna tıklayın
4. Ekrandaki QR kodu veya linki katılımcılarla paylaşın
5. Herkes katıldıktan sonra **OYUNU BAŞLAT** butonuna basın
6. Her soru sonrası **CEVABI GÖSTER** → **SONRAKI SORU** akışını takip edin

### Oyuncu (Katılımcı)
1. QR kodu telefonla okutun veya `http://[IP]:5000/play` adresine gidin
2. Oda kodunu ve adınızı girin
3. Host oyunu başlatana kadar bekleyin
4. Soruları cevaplayın — hızlı cevap bonus puan kazandırır!

## Özellikler

- 🔲 **QR Kod** — Katılım için anında QR kod oluşturma
- 👥 **Çok Oyunculu** — Sınırsız katılımcı
- ⏱ **Zaman Bonusu** — Hızlı cevap = daha fazla puan
- 🔥 **Seri Bonusu** — Arka arkaya doğru cevap
- 💡 **Can Hakları** — 50/50 ve İpucu
- 📊 **Cevap Dağılımı** — Her soru sonrası istatistik
- 🏆 **Canlı Sıralama** — Anlık leaderboard
- ➕ **Soru Ekleme** — Host panelinden özel soru ekle

## Ağ Erişimi

Aynı Wi-Fi ağındaki cihazlar için sunucu IP'sini kullanın:
- Host: `http://localhost:5000`
- Oyuncular: `http://192.168.x.x:5000/play`

Sunucu başladığında IP adresi terminalde görüntülenir.

## Ayarlar

- Host şifresi: `app.py` içinde `host_password` değişkeni
- Varsayılan süre: 20 saniye (oyun başlatılırken değiştirilebilir)
