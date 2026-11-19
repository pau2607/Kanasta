/* El profe de Kanasta — mascota animada en pixel art.
   Vive en una capa fija sobre la página (fuera de Streamlit), así sigue caminando
   aunque la app se vuelva a dibujar. Reacciona a lo que pasa en la tienda leyendo
   los clics, avisos y toasts de la página. */
(() => {
  if (window.KanastaProfe) return;
  const BASE = new URL(".", document.getElementById("kp-js").src).href;   // carpeta de este archivo (sirve local y en Streamlit Cloud)
  const ESC = 2, FW = 48 * ESC, FH = 58 * ESC;          // 96 × 116 px: múltiplo exacto = píxeles nítidos
  const ANIM = {"idle":[140,140,140,140,140,140,140,140,140,140,140,140],"hablar":[110,110,110,110,110,110,110,110],"caminar":[100,100,100,100,100,100,100,100],"saludo":[140,140,140,140,140,140,140,140],"feliz":[80,80,80,80,80,80,80,80,80,80],"celebrar":[80,80,80,80,80,80,80,80,80,80,80,80],"aplaudir":[100,100,100,100,100,100,100,100],"galactico":[110,110,110,110,110,110,110,110,110,110,110,110],"pensar":[200,200,200,200,200,200,200,200],"duda":[140,140,140,140,140,140,140,140],"sorpresa":[90,90,90,90,300,300],"triste":[160,160,160,160,160,160,160,160],"favorito":[110,110,110,110,110,110,110,110],"pina_colada":[200,150,150,200,140,140,140,140,140,140,120,120,120,120,120,120],"bailar":[130,130,130,130,130,130,130,130],"reir":[90,90,90,90,90,90,90,90],"negar":[120,120,120,120,120,120,120,120],"senalar":[150,150,150,150,150,150],"lentes":[200,150,150,110,110,110,110,110,110,110,110,110],"dormir":[160,160,160,160,160,160,160,160,160,160,160,160],"leer":[160,160,160,160,160,160,160,160,160,160,160,160],"retrato":[1000]};                                   // {nombre: [duraciones_ms por frame]}
  const MANOS = { x: FW / 2, y: 74 };                      // dónde lleva el producto (frente al pecho)
  const VEL = 520;                                         // px por segundo al caminar
  const QUIETO = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };
  const leerLS = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const leerSS = (k) => { try { return sessionStorage.getItem(k); } catch (e) { return null; } };
  const guardarSS = (k, v) => { try { sessionStorage.setItem(k, v); } catch (e) {} };
  const dormirMs = (ms) => new Promise((r) => setTimeout(r, ms));

  // ------------------------------------------------------------------ estilos
  const css = document.createElement("style");
  css.textContent = `
  #kp-root{position:fixed;left:0;top:0;width:${FW}px;height:${FH}px;z-index:2147483000;pointer-events:none;
           will-change:transform;}
  #kp-sprite{width:${FW}px;height:${FH}px;image-rendering:pixelated;background-repeat:no-repeat;
             pointer-events:auto;cursor:pointer;filter:drop-shadow(0 3px 2px rgba(0,0,0,.18));}
  #kp-sprite.izq{transform:scaleX(-1);}
  #kp-x{position:absolute;top:-4px;right:-6px;width:22px;height:22px;border-radius:50%;border:none;
        background:#1F1F1F;color:#fff;font:600 13px/22px sans-serif;text-align:center;cursor:pointer;
        opacity:0;transition:opacity .15s;pointer-events:auto;padding:0;}
  #kp-root:hover #kp-x{opacity:.85;}
  .kp-globo{position:absolute;bottom:${FH + 8}px;left:50%;transform:translateX(-50%) scale(.6);opacity:0;z-index:2;
            background:#fff;color:#1F1F1F;border:2px solid #1F1F1F;border-radius:14px;padding:7px 11px;
            font:600 13px/1.3 Poppins,"Segoe UI",sans-serif;width:max-content;max-width:230px;text-align:center;
            box-shadow:3px 3px 0 #1F1F1F;transition:opacity .18s,transform .18s;pointer-events:none;}
  .kp-globo.ver{opacity:1;transform:translateX(-50%) scale(1);}
  .kp-globo.abajo{bottom:auto;top:${FH + 8}px;}
  .kp-globo:after{content:"";position:absolute;left:calc(50% - var(--cola, 0px));bottom:-9px;margin-left:-7px;border:7px solid transparent;
                  border-top-color:#1F1F1F;border-bottom:0;}
  .kp-globo.abajo:after{bottom:auto;top:-9px;border-top:0;border-bottom:7px solid #1F1F1F;}
  .kp-item{position:fixed;z-index:2147483001;font-size:26px;line-height:1;pointer-events:none;
           filter:drop-shadow(0 2px 1px rgba(0,0,0,.25));transition:transform .35s ease,opacity .35s ease;}
  .kp-item.pop{animation:kpPop .35s ease;}
  @keyframes kpPop{0%{transform:scale(.2)}70%{transform:scale(1.35)}100%{transform:scale(1)}}
  .kp-rebote{animation:kpRebote .5s ease;}
  @keyframes kpRebote{0%,100%{transform:scale(1)}35%{transform:scale(1.18) rotate(-4deg)}70%{transform:scale(.94)}}
  #kp-cara{position:fixed;right:16px;bottom:16px;width:52px;height:52px;border-radius:50%;z-index:100000;
           background:#FFF0EB url(${BASE}cara.png) center/80% no-repeat;image-rendering:pixelated;border:2px solid #1F1F1F;
           box-shadow:2px 2px 0 #1F1F1F;cursor:pointer;display:none;}
  `;
  document.head.appendChild(css);

  // precarga de hojas
  Object.keys(ANIM).forEach((n) => { const i = new Image(); i.src = BASE + n + ".png"; });

  // ------------------------------------------------------------------ elementos
  const root = document.createElement("div"); root.id = "kp-root";
  const sprite = document.createElement("div"); sprite.id = "kp-sprite"; sprite.title = "¡Hola! Soy el profe";
  const globo = document.createElement("div"); globo.id = "kp-globo"; globo.className = "kp-globo";
  const cerrar = document.createElement("button"); cerrar.id = "kp-x"; cerrar.textContent = "×";
  cerrar.title = "Ocultar al profe"; cerrar.setAttribute("aria-label", "Ocultar al profe");
  root.append(globo, sprite, cerrar);
  const cara = document.createElement("div"); cara.id = "kp-cara"; cara.title = "Llamar al profe";
  document.body.append(root, cara);

  // ------------------------------------------------------------------ animador de sprites
  const timers = new WeakMap();
  function reproducir(el, nombre, { loop = true } = {}) {
    return new Promise((fin) => {
      clearTimeout(timers.get(el));
      const d = ANIM[nombre];
      el.style.backgroundImage = `url(${BASE}${nombre}.png)`;
      el.style.backgroundSize = `${d.length * FW}px ${FH}px`;
      let i = 0;
      const paso = () => {
        el.style.backgroundPosition = `${-i * FW}px 0`;
        const ms = d[i]; i++;
        if (i >= d.length) {
          if (!loop) { timers.set(el, setTimeout(fin, ms)); return; }
          i = 0;
        }
        timers.set(el, setTimeout(paso, ms));
      };
      paso();
      if (loop) fin();
    });
  }
  let animActual = null;
  const anim = (nombre, o) => { animActual = nombre; return reproducir(sprite, nombre, o); };

  // ------------------------------------------------------------------ posición y caminata
  const pos = { x: 0, y: 0 };
  const limitar = (x, y) => ({
    x: Math.max(4, Math.min(innerWidth - FW - 4, x)),
    y: Math.max(4, Math.min(innerHeight - FH - 4, y)),
  });
  const casa = () => limitar(innerWidth - FW - 150, innerHeight - FH - 6);
  function ubicar(x, y) {
    pos.x = x; pos.y = y; root.style.transform = `translate(${x}px, ${y}px)`;
    if (globo.classList.contains("ver")) ajustarGlobo();
  }
  function caminar(x, y) {
    const p = limitar(x, y);
    const dx = p.x - pos.x, dy = p.y - pos.y, dist = Math.hypot(dx, dy);
    if (dist < 3) return Promise.resolve();
    if (Math.abs(dx) > 2) sprite.classList.toggle("izq", dx < 0);
    if (QUIETO) { ubicar(p.x, p.y); return Promise.resolve(); }
    anim("caminar");
    const t0 = performance.now(), dur = Math.max(350, (dist / VEL) * 1000), x0 = pos.x, y0 = pos.y;
    return new Promise((fin) => {
      const tick = (t) => {
        const k = Math.min(1, (t - t0) / dur);
        const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;   // ease-in-out
        ubicar(x0 + dx * e, y0 + dy * e);
        if (k < 1) requestAnimationFrame(tick); else fin();
      };
      requestAnimationFrame(tick);
    });
  }

  // ------------------------------------------------------------------ globo de diálogo
  let globoTimer = null;
  function ajustarGlobo() {
    const w = globo.offsetWidth, centro = pos.x + FW / 2;
    const c = Math.max(w / 2 + 10, Math.min(innerWidth - w / 2 - 10, centro));
    const off = Math.round(c - centro);
    globo.style.marginLeft = off + "px";
    globo.style.setProperty("--cola", Math.max(-w / 2 + 16, Math.min(w / 2 - 16, off)) + "px");
  }
  function decir(texto, ms = 2800) {
    clearTimeout(globoTimer);
    globo.textContent = texto;
    globo.classList.toggle("abajo", pos.y < 120);
    globo.classList.add("ver");
    ajustarGlobo();
    globoTimer = setTimeout(() => globo.classList.remove("ver"), ms);
  }

  // ------------------------------------------------------------------ cola de acciones
  let cola = Promise.resolve(), ocupado = 0;
  function encolar(fn, siempre = false) {
    ocupado++;
    cola = cola.then(() => (oculto && !siempre ? null : fn())).catch(() => {}).finally(() => { ocupado--; });
    return cola;
  }
  async function reaccion(nombre, texto, veces = 1) {
    if (enMoto) { if (texto && esc) esc.decir(texto); return; }        // va manejando: solo habla
    if (texto) decir(texto, 3000);
    for (let i = 0; i < veces; i++) await anim(nombre, { loop: false });
    anim("idle");
  }

  // ------------------------------------------------------------------ agarrar y llevar al carrito
  function rectCarrito() {
    const a = document.querySelector(".st-key-hdr_carrito a");
    if (!a) return null;
    const r = a.getBoundingClientRect();
    return r.width && r.bottom > 0 ? r : null;
  }
  // dónde está el producto ahora (la tarjeta en la página); si no se ve, lo saca de su bolsillo
  function ubicarOrigen(o) {
    const el = o.tarjeta && document.querySelector("." + o.tarjeta + " .k-tile");
    const hdr = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-hdr)');
    const techo = hdr ? hdr.getBoundingClientRect().bottom : 0;
    if (el) {
      const r = el.getBoundingClientRect();
      const x = r.left + r.width / 2, y = r.top + r.height / 2;
      if (r.width && y > techo + 20 && y < innerHeight - 20 && x > 0 && x < innerWidth) return { x, y, enMano: false };
    }
    return { x: pos.x + MANOS.x, y: pos.y + MANOS.y - 13, enMano: true };
  }
  async function entregar(origen) {
    const o = ubicarOrigen(origen);
    const item = document.createElement("div");
    item.className = "kp-item pop"; item.textContent = origen.emoji || "📦";
    item.style.left = o.x - 13 + "px"; item.style.top = o.y - 13 + "px";
    document.body.appendChild(item);
    if (!o.enMano) await caminar(o.x - MANOS.x, o.y - MANOS.y + 10);  // ir por el producto
    else await dormirMs(350);
    item.classList.remove("pop");
    item.style.position = "absolute";                                  // agarrarlo: ahora viaja con él
    item.style.left = MANOS.x - 13 + "px"; item.style.top = MANOS.y - 26 + "px";
    root.appendChild(item);
    await dormirMs(120);
    const c = rectCarrito();
    const destino = c ? { x: c.left + c.width / 2, y: c.top + c.height / 2 }
                      : { x: innerWidth - 60, y: 40 };
    await caminar(destino.x - MANOS.x, destino.y - MANOS.y + 60);     // llevarlo al carrito
    const r = item.getBoundingClientRect();                            // soltarlo dentro del carrito
    item.style.position = "fixed"; item.style.left = r.left + "px"; item.style.top = r.top + "px";
    document.body.appendChild(item);
    requestAnimationFrame(() => {
      item.style.transform = `translate(${destino.x - r.left - 13}px, ${destino.y - r.top - 13}px) scale(.25)`;
      item.style.opacity = "0";
    });
    setTimeout(() => item.remove(), 400);
    const a = document.querySelector(".st-key-hdr_carrito a");
    if (a) { a.classList.remove("kp-rebote"); void a.offsetWidth; a.classList.add("kp-rebote"); }
    decir(["¡A tu kanasta! 🧺", "¡Listo, ya está en el carrito!", "¡Buena elección! 👌", "Uno más 🛒"][
      Math.floor(Math.random() * 4)], 2200);
    await anim("feliz", { loop: false });
    await caminar(casa().x, casa().y);
    anim("idle");
  }

  // ------------------------------------------------------------------ detectar qué pasa en la página
  let pendiente = null;   // producto que se acaba de agregar (esperando confirmación de la app)
  let ultimaTarjeta = null;  // tarjeta desde la que se abrió el detalle con "Ver"
  const claveTarjeta = (el) => { const c = el && [...el.classList].find((k) => k.startsWith("st-key-card_")); return c || null; };
  function emojiDe(tile) {
    if (!tile) return null;
    const textos = [...tile.childNodes].filter((n) => n.nodeType === 3 && n.textContent.trim());
    return textos.length ? textos[textos.length - 1].textContent.trim() : null;
  }
  document.addEventListener("click", (e) => {
    actividad();
    const b = e.target.closest("button");
    if (!b) return;
    const lineas = (b.innerText || "").split("\n").map((x) => x.trim()).filter(Boolean);
    const t = lineas.length ? lineas[lineas.length - 1] : "";              // sin el nombre del ícono
    if (t === "Ver") {
      ultimaTarjeta = claveTarjeta(b.closest('[class*="st-key-card_"]'));
    } else if (t === "Agregar" || t.startsWith("Agregar ·")) {
      const carta = b.closest('[class*="st-key-card_"]'), dialogo = b.closest('[role="dialog"]');
      const cont = carta || dialogo || b.closest('[data-testid="stVerticalBlockBorderWrapper"]');
      const tile = cont && cont.querySelector(".k-tile");
      // desde el detalle, el profe va a la tarjeta del producto en la página (el detalle se cierra)
      pendiente = { tarjeta: carta ? claveTarjeta(carta) : (dialogo ? ultimaTarjeta : null), emoji: emojiDe(tile), t: Date.now() };
    } else if (t === "Enviar opinión") {
      encolar(() => reaccion("aplaudir", "¡Gracias por opinar! 👏", 2));
    } else if (t.includes("Guardar en favoritos")) {
      encolar(() => reaccion("favorito", "¡A favoritos! 💖"));
    } else if (b.getAttribute("title") === "Quitar" || b.closest('[class*="st-key-del_"]')) {
      encolar(() => reaccion("triste", "Ay… lo quitaste 😢"));
    }
  }, true);

  const textosRecientes = new Map();
  const REGLAS = [
    [/Pago confirmado|pedido ya se está preparando/i, () => encolar(async () => { await reaccion("celebrar", "¡Pago listo! 🎉"); await reaccion("galactico", "¡Eres un galáctico! 🚀"); })],
    [/Cupón .* aplicado/i, () => encolar(() => reaccion("celebrar", "¡Cupón aplicado! 🤑"))],
    [/cupón .*(no existe|venció)/i, () => encolar(() => reaccion("negar", "Ese cupón no va… 🙅‍♂️", 2))],
    [/No encontramos productos/i, () => encolar(() => reaccion("duda", "Hmm… no encuentro eso 🤔", 2))],
    [/código CIP/i, () => encolar(() => reaccion("hablar", "Paga con el código en cualquier agente 😉", 2))],
    [/Pedido cancelado/i, () => encolar(() => reaccion("triste", "Bueno… otra vez será 😢"))],
    [/TransicionInvalida|No se puede \S+ un pedido/i, () => encolar(() => reaccion("negar", "¡No se puede! Lo dice el State 🤓", 2))],
    [/Cerraste sesión/i, () => encolar(() => reaccion("saludo", "¡Hasta pronto! 👋"))],
    [/incorrectos/i, () => encolar(() => reaccion("negar", "Esa no es la contraseña 🔐", 2))],
  ];
  // Streamlit reutiliza el mismo elemento al cambiar un aviso (st.error → st.success),
  // así que comparamos los textos visibles entre un barrido y el siguiente.
  const SEL = '[data-testid="stToast"], [data-testid^="stAlertContent"]';
  let visibles = new Set(), barridoPend = null;
  function barrer() {
    barridoPend = null;
    const ahora = new Set();
    document.querySelectorAll(SEL).forEach((el) => {
      const txt = (el.innerText || "").trim();
      if (txt) ahora.add(txt);
    });
    const t0 = Date.now();
    for (const txt of ahora) {
      if (visibles.has(txt)) continue;                                   // ya estaba en pantalla
      if (t0 - (textosRecientes.get(txt) || 0) < 8000) continue;         // re-dibujado al cambiar de página
      textosRecientes.set(txt, t0);
      for (const [re, fn] of REGLAS) if (re.test(txt)) { fn(); break; }
    }
    visibles = ahora;
  }
  new MutationObserver(() => { if (!barridoPend) barridoPend = setTimeout(barrer, 150); })
    .observe(document.body, { childList: true, subtree: true, characterData: true });

  // cuando el contador del carrito sube, va por el producto que se acaba de agregar
  const contarCarrito = () => {
    const a = document.querySelector(".st-key-hdr_carrito a");
    const m = a && (a.innerText || "").match(/Carrito\s*\((\d+)\)/);
    return a ? (m ? +m[1] : 0) : null;
  };
  let enCarrito = contarCarrito();
  setInterval(() => {
    const n = contarCarrito();
    if (n === null) return;                                   // páginas sin carrito (admin)
    if (enCarrito !== null && n > enCarrito && pendiente && Date.now() - pendiente.t < 8000) {
      const o = pendiente; pendiente = null;
      encolar(() => entregar(o));
    }
    enCarrito = n;
  }, 250);

  // el buscador lo hace pensar
  document.addEventListener("input", (e) => {
    if (e.target.matches && e.target.matches('input[placeholder^="Buscar productos"]') && !ocupado && !durmiendo) {
      anim("pensar"); clearTimeout(volverIdle); volverIdle = setTimeout(() => !ocupado && anim("idle"), 2500);
    }
  }, true);
  let volverIdle = null;

  // ------------------------------------------------------------------ vida propia: pasear, dormir, clic
  let ultimaActividad = Date.now(), durmiendo = false;
  function actividad() {
    ultimaActividad = Date.now();
    if (durmiendo) { durmiendo = false; encolar(() => reaccion("sorpresa", "¡Ah! Estaba despierto, eh 😅")); }
  }
  ["mousemove", "keydown", "scroll", "touchstart"].forEach((ev) =>
    addEventListener(ev, () => { if (durmiendo || Date.now() - ultimaActividad > 2000) actividad(); }, { passive: true }));

  const PASATIEMPOS = [["lentes", "Te recomiendo ver los más vendidos 🤓"], ["leer", null], ["pensar", null], ["idle", null]];
  setInterval(() => {
    if (oculto || ocupado || durmiendo || enMoto) return;
    if (Date.now() - ultimaActividad > 60000) { durmiendo = true; anim("dormir"); decir("Zzz…", 2000); return; }
    if (Math.random() < 0.55) {
      encolar(async () => {
        const c = casa();
        await caminar(30 + Math.random() * (innerWidth - FW - 60), c.y);
        const [n, t] = PASATIEMPOS[Math.floor(Math.random() * PASATIEMPOS.length)];
        if (n !== "idle") await reaccion(n, Math.random() < 0.4 ? t : null);
        await dormirMs(1500);
        await caminar(c.x, c.y);
        anim("idle");
      });
    }
  }, 22000);

  const TRUCOS = [["pina_colada", "¡Regálame una piña colada! 🍍"], ["bailar", "♪ ¡Ofertas que dan ganas de bailar! ♪"],
                  ["reir", "JA JA JA 😂"], ["galactico", "¡Eres un galáctico! 🚀"], ["aplaudir", "¡Bien ahí! 👏"]];
  sprite.addEventListener("click", (e) => {
    e.stopPropagation();
    if (ocupado || enMoto) return;
    const [n, t] = TRUCOS[Math.floor(Math.random() * TRUCOS.length)];
    encolar(() => reaccion(n, t, n === "pina_colada" ? 1 : 2));
  });

  // ------------------------------------------------------------------ reparto en moto (panel admin)
  // La app deja un contenedor .st-key-pista_<id> entre el diagrama de estados y los botones, con los
  // datos del pedido en .kp-pista-info. Aquí se dibuja la pista dentro de ese contenedor.
  const ARTE = 2;                                          // versión de los dibujos (evita la caché)
  const ESC_H = 228, VEREDA = 154, PISTA = 166, VMAX = 270;
  const css2 = document.createElement("style");
  css2.textContent = `
  .kp-escena{position:relative;width:100%;align-self:stretch;flex:0 0 auto;height:${ESC_H}px;margin:2px 0 6px;user-select:none;}
  .kp-esc-fondo{position:absolute;inset:0;border-radius:18px;overflow:hidden;
                background:linear-gradient(#CFEAFF 0%,#EAF6FF 60%,#F6FBFF 100%);border:1px solid #E3E8EE;}
  .kp-capa{position:absolute;left:0;right:0;background-repeat:repeat-x;image-rendering:pixelated;}
  .kp-esc-fondo .kp-vereda{position:absolute;left:0;right:0;top:${VEREDA}px;height:${PISTA - VEREDA}px;
                background:#DCD6CB;border-top:2px solid #C9C2B4;}
  .kp-esc-fondo .kp-pista{position:absolute;left:0;right:0;top:${PISTA}px;bottom:0;background:#5B5F66;
                border-top:3px solid #A9A39A;}
  .kp-esc-fondo .kp-lineas{position:absolute;left:0;right:0;top:${PISTA + 30}px;height:4px;
                background:repeating-linear-gradient(90deg,#F3F1EA 0 30px,transparent 30px 62px);}
  .kp-px{position:absolute;image-rendering:pixelated;background-repeat:no-repeat;pointer-events:none;}
  .kp-actor{position:absolute;left:0;top:0;width:${FW}px;height:${FH}px;pointer-events:none;will-change:transform;}
  .kp-actor .kp-spr{width:${FW}px;height:${FH}px;image-rendering:pixelated;background-repeat:no-repeat;
                    filter:drop-shadow(0 3px 2px rgba(0,0,0,.18));}
  .kp-actor .kp-spr.izq{transform:scaleX(-1);}
  .kp-humo{position:absolute;width:10px;height:10px;border-radius:50%;background:#E9ECEF;opacity:.9;
           animation:kpHumo .9s ease-out forwards;pointer-events:none;}
  @keyframes kpHumo{to{transform:translate(-34px,-16px) scale(2.2);opacity:0}}
  .kp-esc-letrero{position:absolute;right:12px;top:10px;background:#fff;border:2px solid #1F1F1F;border-radius:10px;
           padding:3px 9px;font:600 12px/1.3 Poppins,"Segoe UI",sans-serif;color:#1F1F1F;box-shadow:2px 2px 0 #1F1F1F;}
  `;
  document.head.appendChild(css2);
  ["moto", "moto_profe", "paquete", "casa", "edificios", "nubes", "frente"].forEach((n) => { const i = new Image(); i.src = BASE + "escena/" + n + ".png?v=" + ARTE; });

  const pixel = (clase, img, w, h) => {
    const d = document.createElement("div"); d.className = "kp-px " + clase;
    d.style.cssText = `width:${w * ESC}px;height:${h * ESC}px;background-image:url(${BASE}escena/${img}.png?v=${ARTE});` +
                      `background-size:auto ${h * ESC}px;`;
    return d;
  };
  function actor(alto = FH) {
    const a = document.createElement("div"); a.className = "kp-actor"; a.style.height = alto + "px";
    const s = document.createElement("div"); s.className = "kp-spr"; s.style.height = alto + "px";   // recorta las piernas
    const g = document.createElement("div"); g.className = "kp-globo"; g.style.bottom = alto + 8 + "px";
    a.append(g, s); a.spr = s; a.globo = g; a.style.display = "none";
    return a;
  }

  let esc = null, enMoto = false;

  function crearEscena(cont, datos) {
    const nodo = document.createElement("div"); nodo.className = "kp-escena";
    const fondo = document.createElement("div"); fondo.className = "kp-esc-fondo";
    const capa = (img, top, w, h) => {
      const c = document.createElement("div"); c.className = "kp-capa";
      c.style.cssText += `top:${top}px;height:${h * ESC}px;background-image:url(${BASE}escena/${img}.png?v=${ARTE});` +
                         `background-size:${w * ESC}px ${h * ESC}px;`;
      return c;
    };
    const nubes = capa("nubes", 12, 240, 34), edif = capa("edificios", VEREDA - 100, 256, 50);
    const vereda = document.createElement("div"); vereda.className = "kp-vereda";
    const frente = capa("frente", VEREDA + 4 - 88, 220, 44);
    const pista = document.createElement("div"); pista.className = "kp-pista";
    const lineas = document.createElement("div"); lineas.className = "kp-lineas";
    const casaEl = pixel("", "casa", 64, 58); casaEl.style.top = (VEREDA + 4 - 116) + "px"; casaEl.style.display = "none";
    fondo.append(nubes, edif, vereda, frente, casaEl, pista, lineas);
    const letrero = document.createElement("div"); letrero.className = "kp-esc-letrero";
    const moto = pixel("", "moto", 64, 38), caja = pixel("", "paquete", 16, 13);
    const motoProfe = pixel("", "moto_profe", 64, 64); motoProfe.style.display = "none";   // el profe de perfil manejando
    const jinete = actor(98), peaton = actor();
    jinete.spr.style.visibility = "hidden";                  // el jinete solo sostiene el globo de diálogo
    nodo.append(fondo, letrero, caja, jinete, peaton, moto, motoProfe);
    cont.appendChild(nodo);

    const e = { cont, nodo, datos, v: 0, off: 0, motoX: 46, casaX: null, caja, moto, motoProfe, jinete, peaton, casaEl, letrero,
                rueda: 0, ultimoHumo: 0, vivo: true, cajaEn: "moto" };
    const MOTO_TOP = ESC_H - 10 - 76;
    e.motoTop = MOTO_TOP;
    e.ancho = () => nodo.clientWidth || 800;
    e.posJinete = () => ({ x: e.motoX - 14, y: MOTO_TOP - 64 });
    e.puerta = () => ({ x: e.casaX + 63, y: VEREDA + 4 });
    e.decir = (texto, ms = 3000, quien = e.jinete.style.display !== "none" ? e.jinete : e.peaton) => {
      const g = quien.globo; clearTimeout(g._t); g.textContent = texto; g.classList.add("ver");
      g._t = setTimeout(() => g.classList.remove("ver"), ms);
    };
    let t0 = performance.now();
    const cuadro = (t) => {
      if (!e.vivo) return;
      const dt = Math.min(0.05, (t - t0) / 1000); t0 = t;
      e.off += e.v * dt;
      nubes.style.backgroundPosition = `${-e.off * 0.08}px 0`;
      edif.style.backgroundPosition = `${-e.off * 0.3}px 0`;
      frente.style.backgroundPosition = `${-e.off}px 0`;
      lineas.style.backgroundPosition = `${-e.off}px 0`;
      // la moto: ruedas que giran y un saltito mientras avanza
      if (e.v > 5) e.rueda += e.v * dt / 22;
      const fr = Math.floor(e.rueda) % 2, salto = e.v > 40 && Math.floor(t / 160) % 2 ? -2 : 0;
      moto.style.backgroundPosition = `${-fr * 64 * ESC}px 0`;
      moto.style.transform = `translate(${e.motoX}px, ${MOTO_TOP + salto}px)`;
      motoProfe.style.backgroundPosition = `${-fr * 64 * ESC}px 0`;
      motoProfe.style.transform = `translate(${e.motoX}px, ${MOTO_TOP - 26 * ESC + salto}px)`;
      const pj = e.posJinete();
      jinete.style.transform = `translate(${pj.x}px, ${pj.y + salto}px)`;
      if (e.cajaEn === "moto") caja.style.transform = `translate(${e.motoX - 16}px, ${MOTO_TOP + 6 + salto}px)`;
      if (e.casaX !== null) { casaEl.style.display = ""; casaEl.style.transform = `translateX(${e.casaX}px)`; }
      if (e.v > 60 && t - e.ultimoHumo > 220) {                       // humito del escape
        e.ultimoHumo = t;
        const h = document.createElement("div"); h.className = "kp-humo";
        h.style.left = e.motoX + 14 + "px"; h.style.top = MOTO_TOP + 56 + salto + "px";
        nodo.appendChild(h); setTimeout(() => h.remove(), 950);
      }
      requestAnimationFrame(cuadro);
    };
    requestAnimationFrame(cuadro);
    e.destruir = () => { e.vivo = false; nodo.remove(); };
    return e;
  }

  const tween = (dur, fn) => new Promise((fin) => {
    const t0 = performance.now();
    const tick = (t) => { const k = Math.min(1, (t - t0) / dur); fn(k); if (k < 1) requestAnimationFrame(tick); else fin(); };
    requestAnimationFrame(tick);
  });
  const suave = (k) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2);
  function rectEscena(e) { return e.nodo.getBoundingClientRect(); }

  function ponerJinete(e, v = true) {
    e.jinete.style.display = v ? "" : "none";
    e.motoProfe.style.display = v ? "" : "none";
    e.moto.style.display = v ? "none" : "";
  }
  function letrero(e) {
    const d = e.datos;
    e.letrero.textContent = d.estado === "entregado" ? `🏠 Pedido #${d.pedido} entregado` : `🛵 Pedido #${d.pedido} · ${d.courier}`;
  }
  async function arrancar(e) {
    e.decir(`¡En camino con ${e.datos.courier}! 🛵`, 3200, e.jinete);
    const x0 = e.motoX, x1 = Math.max(150, e.ancho() * 0.24);
    await tween(1600, (k) => { e.v = VMAX * Math.min(1, k * 1.3); e.motoX = x0 + (x1 - x0) * suave(k); });
    e.v = VMAX;
  }

  // salida: el profe camina hasta la moto, se sube y arranca
  async function salir(e) {
    if (!e.vivo) return;
    if (!oculto && !enMoto) {
      const r = rectEscena(e), pj = e.posJinete();
      await caminar(r.left + pj.x, r.top + pj.y);
      if (!e.vivo) return;
      root.style.visibility = "hidden";
    }
    enMoto = true;
    ponerJinete(e);
    await dormirMs(250);
    await arrancar(e);
  }

  // llegada: aparece la casa, frena, baja con el paquete, lo deja en la puerta y vuelve a su lugar
  async function llegar(e) {
    if (!e.vivo) return;
    if (e.motoProfe.style.display === "none") { ponerJinete(e); e.v = VMAX; e.motoX = Math.max(150, e.ancho() * 0.24); }
    const W = e.ancho(), destino = Math.min(W - 150, e.motoX + 150), xi = W + 30;
    let prev = xi;
    e.casaX = xi;
    await tween(2300, (k) => {
      const x = xi + (destino - xi) * (1 - Math.pow(1 - k, 3));
      e.v = Math.max(0, (prev - x) * 60); prev = x; e.casaX = x;     // el fondo corre a la misma velocidad que la casa
    });
    e.v = 0; e.casaX = destino;
    await dormirMs(300);
    if (!e.vivo) return;
    // se baja de la moto con el paquete en las manos
    ponerJinete(e, false);
    const p = e.peaton, desde = { x: e.motoX + 40, y: ESC_H - 8 - FH };
    p.style.display = ""; p.style.transform = `translate(${desde.x}px, ${desde.y}px)`;
    e.cajaEn = "manos"; e.caja.style.zIndex = "3";
    const ponerCaja = (x, y) => { e.caja.style.transform = `translate(${x + FW / 2 - 16}px, ${y + 60}px)`; };
    ponerCaja(desde.x, desde.y);
    const pu = e.puerta(), hasta = { x: pu.x - 112, y: pu.y + 6 - FH };
    p.spr.classList.remove("izq"); reproducir(p.spr, "caminar");
    await tween(Math.max(600, Math.hypot(hasta.x - desde.x, hasta.y - desde.y) / (VEL * 0.45) * 1000), (k) => {
      const x = desde.x + (hasta.x - desde.x) * k, y = desde.y + (hasta.y - desde.y) * k;
      p.style.transform = `translate(${x}px, ${y}px)`; ponerCaja(x, y);
    });
    // deja el paquete en la puerta
    e.cajaEn = "puerta"; e.caja.style.zIndex = "";
    e.caja.style.transition = "transform .3s ease";
    e.caja.style.transform = `translate(${pu.x - 16}px, ${pu.y - 26}px)`;
    setTimeout(() => (e.caja.style.transition = ""), 350);
    e.decir("¡Pedido entregado! 📦", 3000, p);
    await reproducir(p.spr, "feliz", { loop: false });
    await reproducir(p.spr, "aplaudir", { loop: false });
    reproducir(p.spr, "idle");
    await dormirMs(500);
    if (!e.vivo || !enMoto) return;                               // cambió de pedido a mitad de camino
    // vuelve a su lugar de siempre
    if (!oculto) {
      const r = rectEscena(e), m = new DOMMatrix(getComputedStyle(p).transform);
      p.style.display = "none";
      ubicar(...Object.values(limitar(r.left + m.m41, r.top + m.m42)));
      root.style.visibility = ""; enMoto = false;
      sprite.classList.remove("izq");
      decir("¡Misión cumplida! 😎", 2000);
      await caminar(casa().x, casa().y);
      anim("idle");
    } else {
      enMoto = false;
      await tween(500, (k) => (p.style.opacity = String(1 - k)));
      p.style.display = "none"; p.style.opacity = "";
    }
  }

  // escena ya entregada (al abrir un pedido entregado): casa, paquete en la puerta y moto estacionada
  function dejarEntregado(e) {
    const W = e.ancho();
    e.motoX = Math.max(150, W * 0.24); e.casaX = Math.min(W - 150, e.motoX + 150); e.v = 0;
    const pu = e.puerta(); e.cajaEn = "puerta";
    e.caja.style.transform = `translate(${pu.x - 16}px, ${pu.y - 26}px)`;
  }

  function bajarseSinAnimacion() {
    if (!enMoto) return;
    enMoto = false;
    const c = casa(); ubicar(c.x, c.y); root.style.visibility = ""; sprite.classList.remove("izq"); anim("idle");
  }

  setInterval(() => {
    const cont = document.querySelector('[class*="st-key-pista_"]');
    const info = cont && cont.querySelector(".kp-pista-info");
    if (!cont || !info) {                                      // se fue de la página o eligió otro pedido
      if (esc) { esc.destruir(); esc = null; bajarseSinAnimacion(); }
      return;
    }
    const d = { pedido: info.dataset.pedido, estado: info.dataset.estado, courier: info.dataset.courier || "el courier" };
    if (esc && esc.cont === cont && esc.datos.pedido === d.pedido) {
      if (!esc.nodo.isConnected) cont.appendChild(esc.nodo);
      if (esc.datos.estado !== d.estado) {
        const antes = esc.datos.estado; esc.datos = d; letrero(esc);
        if (antes === "enviado" && d.estado === "entregado") { const e = esc; encolar(() => llegar(e), true); }
      }
      return;
    }
    // pedido nuevo en pantalla
    const veniaEnMoto = enMoto;
    if (esc) esc.destruir();
    esc = crearEscena(cont, d); letrero(esc);
    const e = esc;
    if (d.estado === "enviado") {
      if (veniaEnMoto) { ponerJinete(e); e.motoX = Math.max(150, e.ancho() * 0.24); e.v = VMAX; }
      else encolar(() => salir(e), true);
    } else {
      dejarEntregado(e);
      bajarseSinAnimacion();
    }
  }, 300);

  // ------------------------------------------------------------------ ocultar / mostrar
  let oculto = leerLS("kanasta_profe_oculto") === "1";
  function mostrar(v) {
    oculto = !v;
    root.style.display = v ? "" : "none";
    cara.style.display = v ? "none" : "block";
    guardar("kanasta_profe_oculto", v ? "0" : "1");
  }
  cerrar.addEventListener("click", (e) => { e.stopPropagation(); mostrar(false); });
  cara.addEventListener("click", () => { mostrar(true); encolar(() => reaccion("saludo", "¡Volví! 👋")); });

  // ------------------------------------------------------------------ arranque
  addEventListener("resize", () => { if (!ocupado && !enMoto) { const c = casa(); ubicar(c.x, c.y); } });
  const c0 = casa();
  ubicar(c0.x, innerHeight + 10);
  anim("idle");
  mostrar(!oculto);
  if (!oculto) {
    encolar(async () => {
      await caminar(c0.x, c0.y);
      if (!leerSS("kanasta_profe_saludo")) {
        guardarSS("kanasta_profe_saludo", "1");
        await reaccion("saludo", "¡Hola! Soy el profe. Agrega algo y yo te lo llevo a tu kanasta 🧺", 2);
      }
    });
  }
  window.KanastaProfe = { reaccion: (n, t) => encolar(() => reaccion(n, t)), entregar: (o) => encolar(() => entregar(o)) };
})();
