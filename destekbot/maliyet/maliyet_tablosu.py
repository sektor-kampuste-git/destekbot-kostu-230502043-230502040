"""Ölçülmüş maliyet tablosu (SPEC §13): eval koşusunun GERÇEK token sayılarından istek başına ve aylık maliyet.

Önce eval'i çalıştırın (evals/rapor_eval.json oluşur), sonra:
  python maliyet/maliyet_tablosu.py                          # 1.000 kullanıcı × ayda 4 mesaj
  python maliyet/maliyet_tablosu.py --kullanici 5000 --mesaj 6
  python maliyet/maliyet_tablosu.py --model gemini-3.6-flash   # aynı token'larla başka model ne tutardı?
Çıktıyı README "Maliyet" tablosuna yapıştırın. Fiyatlar: cekirdek/fiyatlar.json (ders reposu, Eylül 2026).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from cekirdek import llm  # noqa: E402

KARSILASTIRMA = ["gpt-6-luna", "gemini-3.5-flash-lite", "deepseek-v4.1-flash", "gemini-3.6-flash", "gpt-6-sol"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rapor", default=str(KOK / "evals" / "rapor_eval.json"))
    p.add_argument("--kullanici", type=int, default=1000)
    p.add_argument("--mesaj", type=int, default=4, help="kullanıcı başına aylık mesaj")
    p.add_argument("--model", action="append", help="karşılaştırılacak model(ler)")
    a = p.parse_args()

    yol = Path(a.rapor)
    if not yol.exists():
        raise SystemExit("Önce eval çalıştırın: python evals/eval_calistir.py")
    rapor = json.loads(yol.read_text(encoding="utf-8"))
    olcum = [r for r in rapor["sonuclar"] if "girdi_token" in r]
    if not olcum:
        raise SystemExit("Raporda token ölçümü yok; eval'i yeniden çalıştırın.")
    n = len(olcum)
    girdi = sum(r["girdi_token"] for r in olcum) / n
    cikti = sum(r["cikti_token"] for r in olcum) / n
    adim = sum(r["adim"] for r in olcum) / n
    aylik = a.kullanici * a.mesaj

    print(f"Ölçüm: {n} vaka · {rapor['ozet']['tarih']} · model {rapor['ozet']['model']}")
    print(f"İstek başına ortalama: {girdi:.0f} girdi + {cikti:.0f} çıktı token, {adim:.1f} model çağrısı")
    print(f"Varsayım: {a.kullanici} kullanıcı × ayda {a.mesaj} mesaj = {aylik} istek/ay\n")
    print("| Model | İstek başına | Aylık |")
    print("|---|---:|---:|")
    modeller = [rapor["ozet"]["model"], *(a.model or KARSILASTIRMA)]
    for m in dict.fromkeys(modeller):                 # sırayı koruyarak tekrarları at
        g, c, ok = llm.fiyat_bul(m)
        if not ok:
            continue
        usd = (girdi * g + cikti * c) / 1e6
        etiket = f"{m} (ölçülen)" if m == rapor["ozet"]["model"] else m
        print(f"| {etiket} | ${usd:.5f} | ${usd * aylik:.2f} |")
    print("\nKaldıraçlar: ucuz model kademesi · RAG'de yalnızca 3 parça · max_tokens=500 · "
          "sabit sistem promptunda sağlayıcı önbelleği · bütçe tavanı 0,01 $/istek")


if __name__ == "__main__":
    main()
