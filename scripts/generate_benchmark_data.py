# benchmark icin sahte py dosyalari uretir
import argparse
from pathlib import Path

SABLON = """def fn_{i}():
    TODO = {i}
    return {i}
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-o", "--output", default="benchmark_data")
    p.add_argument("-n", "--count", type=int, default=200)
    args = p.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    for i in range(args.count):
        (out / f"mod_{i}.py").write_text(SABLON.format(i=i), encoding="utf-8")

    print(f"{args.count} dosya olustu -> {out}")


if __name__ == "__main__":
    main()
