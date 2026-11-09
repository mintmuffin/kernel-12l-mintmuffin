# Ticari İşletme Hukuku — Vize Çalışma Kitapçığı

A4, iki sütun, çift yönlü baskıya uygun **43 sayfalık** ders kitapçığı.
Sekiz ders kaydının (D1–D8) düzenlenmiş hâli; sınav öncesi tek kaynaktan çalışmak için kuruldu.

**Çıktı:** [`out/ticaret_hukuku_vize_calisma_kitapcigi.pdf`](out/ticaret_hukuku_vize_calisma_kitapcigi.pdf)

## İçerik

| Bölüm | Ne var |
|---|---|
| Ön söz | Kullanım planı (5 gün), "bu metin ne değildir" kutusu, kitapçığın haritası |
| İçindekiler | 2 sayfa, 153 başlık, sayfa numaralı (PDF'te 146 yer imi) |
| D1–D8 | 126 numaralı alt başlık: kapsam, sistemler, ticari iş, faiz, davalar/arabuluculuk, işletme, şube–unvan–marka, devir, birleşme, teslimsiz taşınır rehni, tacir ve şirket türleri, teyit mektubu–fatura–ihbar |
| Ek A | 13 karşılaştırma tablosu |
| Ek B | 76 soru–cevap (kaparak çalışma düzeni) |
| Ek C | Tek sayfada ticaret hukuku: 16 kural, sayılar tablosu, on klasik hata |
| Ek D | Kaynak eşleştirme, 12 belirsiz nokta, metnin sınırları, künye |
| Dizin | 78 terim, Türkçe alfabetik, sayfa numaralı |

## Yeniden üretmek

```bash
pip install reportlab pymupdf
python3 build.py        # -> out/ticaret_hukuku_vize_calisma_kitapcigi.pdf
```

`build.py` üç geçiş yapar: içindekiler sayfa numaraları, dizin sayfa numaraları, son derleme.
Metin kaynakları `content/*.md`; biçimlendirme `book.py` (stiller, fontlar) ve `engine.py`
(akış öğeleri, ayrıştırıcı, sayfa şablonları).

`convert.py`, 36 sayfalık eski not PDF'ini (`ticaret_hukuku_vize_kitapcigi_compact.pdf`)
`content/*.md` dosyalarına çeviren tek seferlik betiktir; yeniden çalıştırmak üretilmiş
markdown'ı sıfırlar, normalde gerekmez.

## İşaretleme (content/*.md)

```
# D5 | 4. HAFTA · 13 EKİM | Bölüm adı | Tek satır özet
## 5.3 Alt başlık
### Ara başlık
|=Tablo başlığı
| Hücre | Hücre |
- madde
1. numaralı madde
::: ornek Başlık  ... :::      (kutu türleri: kural, ornek, tuzak, karsilastir, belirsiz, ozet)
? soru
  = cevap
!weeks   !notes
```

## Sınırlar

Bu metin ders kayıtlarının düzenlenmiş hâlidir; güncel mevzuat kontrolü yapılmış bir hukuk
görüşü değildir. Faiz oranları, parasal eşikler ve madde numaraları transkriptteki bağlamıyla
verilmiştir; belirsiz kalan yerler Ek D'de listelenmiştir.

## Yazı tipleri

Source Serif 4 (metin) ve Inter (başlık, tablo) — SIL Open Font License 1.1.
`fonts/` altındaki dosyalar Google Fonts değişken yazı tiplerinden sabit kesimlerdir.
