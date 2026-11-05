"""DestekBot araçlarının MCP (Model Context Protocol) sunucusu — Hafta 7.

Aynı araçlar (cekirdek/araclar.py) VS Code Copilot, Claude Desktop, Cursor gibi herhangi bir MCP istemcisine açılır.
Oturum: MCP_MUSTERI_ID ortam değişkeni (varsayılan M-01). Sahiplik kuralı burada da geçerlidir.

Çalıştırma (stdio; istemci bu süreci kendisi başlatır):  python mcp_sunucu.py
"""
from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from cekirdek import araclar, rag

sunucu = MCPServer("destekbot")
OTURUM = araclar.Oturum(os.getenv("MCP_MUSTERI_ID", "M-01"))


@sunucu.tool()
def siparis_durumu(siparis_no: str) -> str:
    """Oturumdaki müşterinin siparişinin ürününü, durumunu ve kargo takip numarasını döndürür (örn. SIP-1001)."""
    return araclar.json_metin(araclar.siparis_durumu(OTURUM, siparis_no))


@sunucu.tool()
def kargo_takip(takip_no: str) -> str:
    """Oturumdaki müşterinin kargo takip numarasının (örn. TK-77) hareket geçmişini döndürür."""
    return araclar.json_metin(araclar.kargo_takip(OTURUM, takip_no))


@sunucu.tool()
def iade_uygunluk_kontrol(siparis_no: str, sebep: str = "fikir_degisikligi", kutu_acildi_mi: bool | None = None) -> str:
    """Siparişin iade/değişim politikasına uygunluğunu ve teslimden bu yana geçen gün sayısını hesaplar."""
    return araclar.json_metin(araclar.iade_uygunluk_kontrol(OTURUM, siparis_no, sebep, kutu_acildi_mi))


@sunucu.tool()
def iade_talebi_olustur(siparis_no: str, sebep: str = "fikir_degisikligi", gerekce: str = "",
                        kutu_acildi_mi: bool | None = None) -> str:
    """İade talebi açar; onaylamaz. Talep müşteri temsilcisinin onayına gider."""
    return araclar.json_metin(araclar.iade_talebi_olustur(OTURUM, siparis_no, sebep, gerekce, kutu_acildi_mi))


@sunucu.tool()
def politika_ara(soru: str) -> str:
    """Bulut mağaza politikalarında arama yapar; en ilgili 3 maddeyi kaynağıyla döndürür."""
    return araclar.json_metin(araclar.politika_ara(OTURUM, soru))


@sunucu.resource("bulut://politikalar")
def politikalar() -> str:
    """Tüm mağaza politikaları, madde madde."""
    return "\n".join(f"[{p.belge} {p.bolum}] {p.baslik}: {p.metin}" for p in rag.indeks().parcalar)


if __name__ == "__main__":
    sunucu.run(transport="stdio")
