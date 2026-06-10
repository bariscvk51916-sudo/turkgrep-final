# Final Ödev Raporu

**Ad Soyad:** Baris  
**Ders:** Sistem Programlama (Görsel Programlama ile ortak ödev)  
**Konu:** Kod dosyalarında arama ve değiştirme aracı  
**GitHub:** https://github.com/bariscvk51916-sudo/turkgrep-final

---

## 1. Ödevin özeti

Hocamız ripgrep (rg) benzeri bir araç istedi. Bu araç kod satırlarında arama yapacak, ayrıca değiştirme de destekleyecek. Konsoldan çalışması yeterli ama görsel programlama tarafı için arayüz de eklenebilir demişti. Ben Python ile yazdım çünkü hem Windows'ta hem Linux'ta rahat çalışıyor.

## 2. Ben ne yaptım?

Projenin adı **TurkGrep**. Komuttan `py -m turkgrep` veya kurulumdan sonra `tg` ile çalışıyor.

Yaptığım şeyler kısaca:

- Dizin içinde paralel arama (thread ile birden fazla dosyaya bakıyor)
- Regex ve düz metin arama
- `.gitignore` varsa ona uyuyor, `node_modules` gibi klasörleri atlıyor
- `-r` ile satır içi değiştirme
- `--dry-run` ile önce gösterip sonra uygulama
- `--backup` ile `.bak` alıyor
- `--json` çıktı (sonuçları düzgün formatta almak için)
- `--benchmark` ile ripgrep süresine bakma
- Tkinter ile basit GUI (`py -m turkgrep.gui`)

Kaynak dosyalar `turkgrep/` klasöründe: `searcher.py` arama, `replacer.py` değiştirme, `cli.py` komut satırı, `gui.py` arayüz.

## 3. Denemeler

Kendi bilgisayarımda (Windows 11, Python 3.14) test ettim.

**test_samples** (3 dosya):
```
TurkGrep :  3.2 ms
Ripgrep  : 20.3 ms
```
Burada benim araç daha hızlı çıktı.

**benchmark_data** (200 dosya, script ile ürettim):
```
TurkGrep : 57 ms
Ripgrep  : 33 ms
```
Çok dosyada ripgrep önde. Muhtemelen Rust ile yazıldığı için. Ama benim tarafta replace, json, gui gibi ekstra işler var.

## 4. Nasıl çalıştırılır?

```
cd turkgrep-final
py -m pip install -e .

py -m turkgrep "TODO" test_samples/ -n
py -m turkgrep "TODO" -r "YAPILACAK" test_samples/ --dry-run
py -m turkgrep --benchmark "def" test_samples/
py -m turkgrep.gui
```

## 5. Sonuç

Ödevde istenen arama + değiştirme kısmını yaptım. Ripgrep kadar her senaryoda hızlı değil ama özellik olarak replace tarafı ve arayüz tarafı dolu. Hoca sunumda araclari karsilastiracagini soyledi, o yuzden `--json` ve `--benchmark` ekledim.

Kaynak kod: yukarıdaki GitHub linki
