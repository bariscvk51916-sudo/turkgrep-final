# TurkGrep

Sistem programlama final ödevi. Ripgrep gibi dosyalarda arama yapan ama aynı zamanda satır değiştirme de yapabilen küçük bir konsol aracı.

Python 3.10+ ile yazıldı. Windows'ta denedim, Ubuntu'da da `install.sh` ile kurulması lazım.

## Ne yapıyor?

- Klasörde veya dosyada metin/regex arar
- Bulunan satırları değiştirir (`-r`)
- Değiştirmeden önce `--dry-run` ile gösterir
- İstersek `--json` ile çıktı alırız
- `--benchmark` ile ripgrep ile süre karşılaştırması yapar
- `turkgrep.gui` ile basit pencere arayüzü var

Ripgrep'te olmayan kısım daha çok replace tarafı. Küçük projelerde hız fena değil, çok dosyada rg biraz öne geçiyor (raporda yazdım).

## Kurulum

Windows:
```
py -m pip install -e .
```

veya `install.ps1` çalıştır.

Linux:
```
python3 -m pip install -e .
```

## Kullanım

Arama:
```
py -m turkgrep "TODO" test_samples/ -n
py -m turkgrep -i "def" --type py .
```

Değiştirme:
```
py -m turkgrep "TODO" -r "YAPILACAK" test_samples/ --dry-run
py -m turkgrep "eski" -r "yeni" dosya.py --backup
```

Diğer:
```
py -m turkgrep --json "class" test_samples/
py -m turkgrep --benchmark "TODO" test_samples/
py -m turkgrep.gui
```

Test:
```
py -m unittest tests/test_turkgrep.py -v
```

Benchmark için çok dosya lazımsa:
```
py scripts/generate_benchmark_data.py -n 200
py -m turkgrep --benchmark "TODO" benchmark_data/
```

## Dosyalar

- `turkgrep/` ana kod
- `tests/` testler
- `test_samples/` deneme dosyaları
- `scripts/` benchmark verisi üretmek için
