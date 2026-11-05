// Temsilci paneli: iade talebi onayı/reddi (İNSAN ONAYI NOKTASI) ve iz/maliyet görünümü.
// Müşteriden gelen gerekçe textContent ile basılır; içindeki HTML/script çalışmaz (SPEC K13).
"use strict";

const $ = (s) => document.querySelector(s);
const el = (etiket, sinif, metin) => {
  const e = document.createElement(etiket);
  if (sinif) e.className = sinif;
  if (metin !== undefined) e.textContent = metin;
  return e;
};

const SINIR = { elektronik: 14, giyim: 30, ev: 14, gida: 2 };
const DURUM_METNI = { onay_bekliyor: "Bekliyor", onaylandi: "Onaylandı", reddedildi: "Reddedildi" };
const UYGUNLUK_METNI = { uygun: "Politikaya uygun", emin_degil: "Kontrol gerekli", uygun_degil: "Uygun değil" };
const SEBEP_METNI = { fikir_degisikligi: "Fikir değişikliği", arizali: "Arızalı", hasarli_teslimat: "Hasarlı teslimat", yanlis_urun: "Yanlış ürün", diger: "Diğer" };
const sayi = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 6 });
const tarih = (iso) => (iso ? new Date(iso).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "");

const durum = { filtre: "onay_bekliyor", secili: null, anahtar: "" };
try { durum.anahtar = sessionStorage.getItem("panel_anahtari") || ""; } catch (_) { /* depolama kapalı */ }

class YetkiHatasi extends Error {}

async function istek(yol, secenek = {}) {
  const yanit = await fetch(yol, {
    ...secenek,
    headers: { "Content-Type": "application/json", "X-Panel-Anahtari": durum.anahtar },
  });
  let govde = null;
  try { govde = await yanit.json(); } catch (_) { /* boş */ }
  if (yanit.status === 401) throw new YetkiHatasi((govde && govde.detail) || "Panel anahtarı gerekli.");
  if (!yanit.ok) throw new Error((govde && typeof govde.detail === "string" && govde.detail) || `Sunucu hatası (${yanit.status}).`);
  return govde;
}

function anahtarIste(mesaj) {
  const kap = $("#ayrinti");
  const form = el("form", "anahtar");
  const etiket = el("label", "", mesaj);
  const girdi = el("input");
  girdi.type = "password";
  girdi.id = "anahtar";
  etiket.htmlFor = "anahtar";
  const b = el("button", "dugme", "Paneli aç");
  b.type = "submit";
  form.append(etiket, girdi, b);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    durum.anahtar = girdi.value;
    try { sessionStorage.setItem("panel_anahtari", durum.anahtar); } catch (_) { /* yok say */ }
    yenile();
  });
  kap.replaceChildren(form);
  girdi.focus();
}

// ---------------------------------------------------------------- talep kuyruğu
async function talepleriYukle() {
  const liste = await istek(`/api/talepler${durum.filtre ? `?durum=${durum.filtre}` : ""}`);
  const ul = $("#talepler");
  ul.replaceChildren();
  if (!liste.length) {
    ul.append(el("li", "bos", durum.filtre ? "Bekleyen talep yok. Müşteri ekranından bir iade talebi açıldığında burada görünür." : "Henüz talep yok."));
    return;
  }
  liste.forEach((t) => {
    const li = el("li");
    const b = el("button", "etiket");
    b.type = "button";
    b.setAttribute("aria-pressed", String(durum.secili === t.id));
    b.append(el("span", "no", t.siparis_no), el("span", `damga ${t.durum}`, DURUM_METNI[t.durum] || t.durum),
             el("span", "urun", `${t.urun}, ${SEBEP_METNI[t.sebep] || t.sebep}`), el("span", "tarih", tarih(t.olusturma)));
    b.addEventListener("click", () => { durum.secili = t.id; ayrintiGoster(t); talepleriYukle(); });
    li.append(b);
    ul.append(li);
  });
}

function ayrintiGoster(t) {
  const kap = $("#ayrinti");
  const parcalar = [el("h1", "", t.siparis_no), el("p", "urun", t.urun)];

  const sinir = SINIR[t.kategori] || 14;
  const gun = el("div", "gunler");
  const serit = el("div", "serit");
  const dolu = el("div", "dolu" + (t.gun_sayisi > sinir ? " asti" : ""));
  dolu.style.width = `${Math.min(100, (t.gun_sayisi / sinir) * 100)}%`;
  serit.append(dolu);
  serit.setAttribute("role", "img");
  serit.setAttribute("aria-label", `Teslimden bu yana ${t.gun_sayisi} gün, sınır ${sinir} gün`);
  gun.append(serit, el("p", "", `Teslimden bu yana ${t.gun_sayisi} gün geçti; ${t.kategori} için sınır ${sinir} gün (${t.kural}).`));
  parcalar.push(gun);

  const dl = el("dl", "bilgiler");
  [["Botun önerisi", UYGUNLUK_METNI[t.uygunluk] || t.uygunluk], ["Sebep", SEBEP_METNI[t.sebep] || t.sebep],
   ["Kategori", t.kategori], ["Müşteri", t.musteri_id], ["Talep zamanı", tarih(t.olusturma)], ["Durum", DURUM_METNI[t.durum]]]
    .forEach(([k, v]) => { const d = el("div"); d.append(el("dt", "", k), el("dd", "", v)); dl.append(d); });
  parcalar.push(dl);

  parcalar.push(el("p", "", "Müşterinin anlattığı"), el("div", "gerekce", t.gerekce || "Müşteri gerekçe yazmadı."));

  if (t.durum === "onay_bekliyor") {
    const form = el("form", "karar");
    const ad = el("label", "", "Temsilci adı");
    const adGirdi = el("input"); adGirdi.required = true; adGirdi.minLength = 2; adGirdi.maxLength = 60; adGirdi.autocomplete = "name";
    ad.append(adGirdi);
    const not = el("label", "tam", "Müşteriye not (isteğe bağlı)");
    const notGirdi = el("textarea"); notGirdi.rows = 2; notGirdi.maxLength = 300;
    not.append(notGirdi);
    const onay = el("button", "dugme onayla", "İadeyi onayla"); onay.type = "submit"; onay.value = "onaylandi";
    const ret = el("button", "dugme reddet", "Talebi reddet"); ret.type = "submit"; ret.value = "reddedildi";
    const hata = el("p", "bildirim tam"); hata.hidden = true;
    form.append(ad, not, onay, ret, hata);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const karar = e.submitter ? e.submitter.value : "onaylandi";
      try {
        const guncel = await istek(`/api/talepler/${t.id}/karar`, { method: "POST",
          body: JSON.stringify({ karar, temsilci: adGirdi.value, notu: notGirdi.value }) });
        ayrintiGoster(guncel);
        talepleriYukle();
      } catch (h) { hata.textContent = h.message; hata.hidden = false; }
    });
    parcalar.push(form);
  } else {
    parcalar.push(el("p", "karar-sonuc", `${DURUM_METNI[t.durum]}: ${t.karar_veren || ""}, ${tarih(t.karar_zamani)}${t.karar_notu ? `. Not: ${t.karar_notu}` : ""}`));
  }
  kap.replaceChildren(...parcalar);
}

// ---------------------------------------------------------------- izler ve maliyet
async function izleriYukle() {
  const { ozet, izler } = await istek("/api/izler?limit=25");
  const sayilar = $("#sayilar");
  sayilar.replaceChildren();
  [[String(ozet.istek), "konuşma"], [`${sayi.format(ozet.ortalama_usd)} $`, "istek başına ortalama"],
   [`${sayi.format(ozet.toplam_usd)} $`, "toplam maliyet"], [`${(ozet.ortalama_ms / 1000).toFixed(1)} sn`, "ortalama süre"],
   [String(ozet.guvenlik_mudahalesi), "güvenlik filtresi devreye girdi"]]
    .forEach(([b, s]) => { const d = el("div"); d.append(el("b", "", b), el("span", "", s)); sayilar.append(d); });

  const tablo = $("#izler");
  tablo.replaceChildren();
  const bas = el("tr");
  ["Zaman", "Müşteri", "Mesaj", "Niyet", "Araçlar", "Token", "Maliyet", "Süre", "Not"].forEach((h) => bas.append(el("th", "", h)));
  const thead = el("thead"); thead.append(bas); tablo.append(thead);
  const tbody = el("tbody");
  izler.forEach((i) => {
    const tr = el("tr");
    const araclar = (() => { try { return JSON.parse(i.araclar).join(", "); } catch (_) { return ""; } })();
    [[tarih(i.zaman)], [i.musteri_id], [i.mesaj.length > 70 ? `${i.mesaj.slice(0, 70)}…` : i.mesaj], [i.niyet || ""], [araclar],
     [String(i.girdi_token + i.cikti_token), "sayi"], [`${sayi.format(i.maliyet_usd)} $`, "sayi"], [`${(i.sure_ms / 1000).toFixed(1)} sn`, "sayi"],
     [[i.durdurma, i.guvenlik && `filtre: ${i.guvenlik}`].filter(Boolean).join("; ")]]
      .forEach(([v, s]) => tr.append(el("td", s || "", v)));
    tbody.append(tr);
  });
  tablo.append(tbody);
}

async function yenile() {
  try {
    await Promise.all([talepleriYukle(), izleriYukle()]);
    if (!durum.secili) $("#ayrinti").replaceChildren(el("p", "bos", "Soldan bir talep seç. Bot talebi açar ve politikaya uygunluğunu hesaplar; onay ya da ret kararını burada sen verirsin."));
  } catch (h) {
    if (h instanceof YetkiHatasi) anahtarIste(durum.anahtar ? "Anahtar hatalı. Panel anahtarını yeniden gir." : "Paneli açmak için panel anahtarını gir.");
    else $("#ayrinti").replaceChildren(el("p", "bildirim", h.message));
  }
}

document.querySelectorAll(".sekmeler button").forEach((b) => b.addEventListener("click", () => {
  durum.filtre = b.dataset.durum;
  document.querySelectorAll(".sekmeler button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  talepleriYukle().catch(() => {});
}));

yenile();
