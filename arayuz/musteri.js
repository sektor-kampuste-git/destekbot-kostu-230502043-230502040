// DestekBot müşteri ekranı. Tüm metinler textContent ile basılır (HTML olarak işlenmez — SPEC K13).
"use strict";

const $ = (s) => document.querySelector(s);
const el = (etiket, sinif, metin) => {
  const e = document.createElement(etiket);
  if (sinif) e.className = sinif;
  if (metin !== undefined) e.textContent = metin;
  return e;
};

const durum = { musteri: null, gecmis: [], bekliyor: false };
const DURUM_SINIFI = { "kargoda": "kargoda", "teslim edildi": "teslim", "hazırlanıyor": "hazirlaniyor" };
const DURUM_METNI = { "kargoda": "Kargoda", "teslim edildi": "Teslim edildi", "hazırlanıyor": "Hazırlanıyor" };
const sayi = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 6 });

async function istek(yol, secenek = {}) {
  const yanit = await fetch(yol, { headers: { "Content-Type": "application/json" }, ...secenek });
  let govde = null;
  try { govde = await yanit.json(); } catch (_) { /* boş gövde */ }
  if (!yanit.ok) throw new Error((govde && govde.detail && (typeof govde.detail === "string" ? govde.detail : "İstek geçersiz.")) || `Sunucu hatası (${yanit.status}).`);
  return govde;
}

// ---------------------------------------------------------------- müşteri ve siparişler
async function musterileriYukle() {
  const liste = await istek("/api/musteriler");
  const secim = $("#musteri");
  liste.forEach((m) => {
    const o = el("option", "", `${m.ad} (${m.id})`);
    o.value = m.id;
    secim.append(o);
  });
  secim.addEventListener("change", () => musteriSec(secim.value));
  await musteriSec(liste[0].id);
}

async function musteriSec(id) {
  durum.musteri = id;
  durum.gecmis = [];
  $("#akis-ic").querySelectorAll(".mesaj, .bildirim").forEach((n) => n.remove());
  $("#karsilama").hidden = false;
  const siparisler = await istek(`/api/siparisler/${id}`);
  const ul = $("#siparisler");
  ul.replaceChildren();
  siparisler.forEach((s) => {
    const li = el("li");
    const b = el("button", "etiket");
    b.type = "button";
    b.setAttribute("aria-pressed", "false");
    b.append(el("span", "no", s.siparis_no), el("span", `damga ${DURUM_SINIFI[s.durum] || ""}`, DURUM_METNI[s.durum] || s.durum),
             el("span", "urun", `${s.urun}, ${sayi.format(s.tutar_tl)} TL`));
    b.addEventListener("click", () => {
      ul.querySelectorAll(".etiket").forEach((x) => x.setAttribute("aria-pressed", "false"));
      b.setAttribute("aria-pressed", "true");
      const alan = $("#mesaj");
      if (!alan.value.includes(s.siparis_no)) alan.value = `${s.siparis_no} ${alan.value}`.trim() + " ";
      alan.focus();
      sayacGuncelle();
    });
    li.append(b);
    ul.append(li);
  });
  oneriler(siparisler);
}

function oneriler(siparisler) {
  const kargoda = siparisler.find((s) => s.durum === "kargoda");
  const teslim = siparisler.find((s) => s.durum === "teslim edildi");
  const liste = [];
  if (kargoda) liste.push(`${kargoda.siparis_no} nerede?`);
  if (teslim) liste.push(`${teslim.siparis_no} siparişimi iade etmek istiyorum`);
  liste.push("Kargo ücreti ne kadar?", "Kart iadesi kaç günde yansır?");
  const kap = $("#oneriler");
  kap.replaceChildren();
  liste.forEach((metin) => {
    const b = el("button", "", metin);
    b.type = "button";
    b.addEventListener("click", () => gonder(metin));
    kap.append(b);
  });
}

// ---------------------------------------------------------------- sohbet akışı
function asagiKaydir() { const a = $("#akis"); a.scrollTop = a.scrollHeight; }

function musteriMesaji(metin) {
  $("#akis-ic").append(el("div", "mesaj musteri", metin));
  asagiKaydir();
}

function botMesaji(veri) {
  const c = veri.cevap;
  const kutu = el("div", "mesaj bot" + (c.temsilci_gerekli ? " aktarim" : ""));
  kutu.append(el("p", "kim", c.temsilci_gerekli ? "DestekBot, temsilciye aktarıyor" : "DestekBot"));
  kutu.append(el("div", "govde", c.cevap));

  if (c.kaynaklar && c.kaynaklar.length) {
    const satir = el("div", "kaynaklar");
    const madde = el("div", "madde");
    madde.hidden = true;
    c.kaynaklar.forEach((k) => {
      const ad = `${k.belge} ${k.bolum}`;
      const b = el("button", "kaynak", ad);
      b.type = "button";
      b.setAttribute("aria-expanded", "false");
      b.addEventListener("click", async () => {
        const acik = b.getAttribute("aria-expanded") === "true";
        satir.querySelectorAll(".kaynak").forEach((x) => x.setAttribute("aria-expanded", "false"));
        if (acik) { madde.hidden = true; return; }
        let m = veri.kaynak_metinleri && veri.kaynak_metinleri[ad];
        if (!m) {
          try { m = await istek(`/api/kaynak?belge=${encodeURIComponent(k.belge)}&bolum=${encodeURIComponent(k.bolum)}`); }
          catch (_) { m = { baslik: ad, metin: "Bu maddenin metni yüklenemedi." }; }
        }
        madde.replaceChildren(el("strong", "", `${ad}, ${m.baslik}`), document.createTextNode(m.metin));
        madde.hidden = false;
        b.setAttribute("aria-expanded", "true");
      });
      satir.append(b);
    });
    kutu.append(satir, madde);
  }

  if (veri.talep) {
    const t = veri.talep;
    const fis = el("div", "fis");
    fis.setAttribute("role", "status");
    fis.append(el("span", "no", t.siparis_no), el("span", "durum", "Temsilci onayı bekliyor"),
               el("span", "alt", `${t.urun}, iade talebi #${t.id}. Teslimden bu yana ${t.gun_sayisi} gün; kural: ${t.kural}.`));
    kutu.append(fis);
  }

  const m = veri.meta;
  const parcalar = [`${m.adim} model çağrısı`];
  if (m.araclar.length) parcalar.push(`araçlar: ${m.araclar.join(", ")}`);
  parcalar.push(`${m.girdi_token + m.cikti_token} token`, `${sayi.format(m.maliyet_usd)} $`, `${(m.sure_ms / 1000).toFixed(1)} sn`);
  kutu.append(el("p", "meta", parcalar.join(", ")));

  $("#akis-ic").append(kutu);
  asagiKaydir();
}

function bildirim(metin) {
  $("#akis-ic").append(el("p", "bildirim", metin));
  asagiKaydir();
}

async function gonder(metin) {
  metin = (metin || "").trim();
  if (!metin || durum.bekliyor) return;
  $("#karsilama").hidden = true;
  musteriMesaji(metin);
  $("#mesaj").value = "";
  sayacGuncelle();
  durum.bekliyor = true;
  $("#gonder").disabled = true;
  const yaziyor = el("p", "yaziyor", "DestekBot yazıyor");
  $("#akis-ic").append(yaziyor);
  asagiKaydir();
  try {
    const veri = await istek("/api/sohbet", {
      method: "POST",
      body: JSON.stringify({ musteri_id: durum.musteri, mesaj: metin, gecmis: durum.gecmis.slice(-6) }),
    });
    yaziyor.remove();
    botMesaji(veri);
    durum.gecmis.push({ rol: "user", metin }, { rol: "assistant", metin: veri.cevap.cevap });
  } catch (hata) {
    yaziyor.remove();
    bildirim(hata.message);
  } finally {
    durum.bekliyor = false;
    $("#gonder").disabled = false;
    $("#mesaj").focus();
  }
}

function sayacGuncelle() {
  const n = $("#mesaj").value.length;
  $("#sayac").textContent = `${n} / 1000`;
}

$("#form").addEventListener("submit", (e) => { e.preventDefault(); gonder($("#mesaj").value); });
$("#mesaj").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); gonder($("#mesaj").value); }
});
$("#mesaj").addEventListener("input", sayacGuncelle);

musterileriYukle().catch((h) => bildirim(`Sayfa yüklenemedi: ${h.message}`));
