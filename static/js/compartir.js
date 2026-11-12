/*
 * Botón «Compartir» (templates/_compartir.html): abre una ventanita con las opciones.
 *   WhatsApp · Facebook · X · Telegram · Correo · Copiar enlace
 *   y «Más opciones», que abre el menú de compartir del teléfono o de la computadora
 *   (ahí aparecen TikTok, Instagram, Messenger… si están instalados). Solo se muestra si el
 *   navegador lo permite.
 *
 * TikTok e Instagram no tienen un enlace web para compartir, por eso no tienen botón propio.
 * WhatsApp en la PC usa la elección de static/js/whatsapp.js (WhatsApp Web o la app) si ya se guardó.
 * Cada red abre en una pestaña nueva; nada se envía sin que la persona lo confirme en esa red.
 */
(function () {
  "use strict";

  var CLAVE_WHATSAPP = "nexalys_whatsapp_modo";  // la misma que usa whatsapp.js
  var menu = null, botonActual = null;

  function esComputadora() {
    var ua = navigator.userAgent || "";
    if (navigator.userAgentData && navigator.userAgentData.mobile) return false;
    if (/Android|iPhone|iPad|iPod|Mobile|Silk|Kindle/i.test(ua)) return false;
    if (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) return false;
    return window.matchMedia ? window.matchMedia("(pointer: fine)").matches : true;
  }

  function modoWhatsApp() {
    try { return localStorage.getItem(CLAVE_WHATSAPP); } catch (e) { return null; }
  }

  // ---------- Enlaces de cada red ----------
  function enlaces(d) {
    var url = encodeURIComponent(d.url);
    var texto = encodeURIComponent(d.texto || d.titulo || "");
    var mensaje = encodeURIComponent((d.texto ? d.texto + " " : "") + d.url);
    var whatsapp = "https://wa.me/?text=" + mensaje;  // celular: abre la app
    if (esComputadora()) {
      whatsapp = modoWhatsApp() === "app" ? "whatsapp://send?text=" + mensaje : "https://web.whatsapp.com/send?text=" + mensaje;
    }
    return {
      whatsapp: whatsapp,
      facebook: "https://www.facebook.com/sharer/sharer.php?u=" + url,
      x: "https://twitter.com/intent/tweet?url=" + url + "&text=" + texto,
      telegram: "https://t.me/share/url?url=" + url + "&text=" + texto,
      correo: "mailto:?subject=" + encodeURIComponent(d.titulo || "NEXALYS Tec") + "&body=" + mensaje,
    };
  }

  // ---------- Copiar el enlace ----------
  function avisar(texto) {
    var aviso = document.getElementById("aviso-compartir");
    if (!aviso) return;
    document.getElementById("aviso-compartir-texto").textContent = texto;
    if (window.bootstrap) window.bootstrap.Toast.getOrCreateInstance(aviso, { delay: 4000 }).show();
  }

  function copiarConTextoOculto(texto) {
    // Para navegadores sin acceso al portapapeles (p. ej. una página abierta sin HTTPS).
    var campo = document.createElement("textarea");
    campo.value = texto;
    campo.setAttribute("readonly", "");
    campo.style.position = "fixed";
    campo.style.opacity = "0";
    document.body.appendChild(campo);
    campo.select();
    var copiado = false;
    try { copiado = document.execCommand("copy"); } catch (e) { copiado = false; }
    document.body.removeChild(campo);
    return copiado;
  }

  function copiar(url) {
    var listo = function () { avisar("Enlace copiado. Pégalo donde quieras compartirlo."); };
    var fallo = function () { avisar("No se pudo copiar. Copia este enlace: " + url); };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(url).then(listo, function () {
        if (copiarConTextoOculto(url)) listo(); else fallo();
      });
    } else if (copiarConTextoOculto(url)) {
      listo();
    } else {
      fallo();
    }
  }

  // ---------- Ventanita ----------
  function opcion(tipo, icono, nombre, href) {
    var el = document.createElement(href ? "a" : "button");
    el.className = "menu-compartir__opcion menu-compartir__opcion--" + tipo;
    el.dataset.opcion = tipo;
    if (href) {
      el.href = href;
      if (href.indexOf("http") === 0) { el.target = "_blank"; el.rel = "noopener"; }
    } else {
      el.type = "button";
    }
    el.innerHTML = '<i class="bi ' + icono + '" aria-hidden="true"></i><span>' + nombre + "</span>";
    return el;
  }

  function cerrarMenu(devolverFoco) {
    if (!menu) return;
    menu.remove();
    menu = null;
    if (devolverFoco && botonActual) botonActual.focus();
  }

  function ubicar(caja, boton) {
    var r = boton.getBoundingClientRect(), margen = 8;
    var ancho = caja.offsetWidth, alto = caja.offsetHeight;
    var izquierda = Math.min(Math.max(margen, r.left), window.innerWidth - ancho - margen);
    var arriba = r.bottom + 6;
    if (arriba + alto > window.innerHeight - margen && r.top - alto - 6 > margen) arriba = r.top - alto - 6;
    caja.style.left = izquierda + "px";
    caja.style.top = Math.max(margen, arriba) + "px";
  }

  function mostrarMenu(boton) {
    cerrarMenu(false);
    botonActual = boton;
    var d = { titulo: boton.dataset.titulo, texto: boton.dataset.texto, url: boton.dataset.url };
    var e = enlaces(d);

    menu = document.createElement("div");
    menu.className = "menu-compartir";
    menu.setAttribute("role", "dialog");
    menu.setAttribute("aria-label", "Compartir");
    menu.innerHTML = '<p class="menu-compartir__titulo">Compartir en…</p>';
    var rejilla = document.createElement("div");
    rejilla.className = "menu-compartir__rejilla";
    rejilla.appendChild(opcion("whatsapp", "bi-whatsapp", "WhatsApp", e.whatsapp));
    rejilla.appendChild(opcion("facebook", "bi-facebook", "Facebook", e.facebook));
    rejilla.appendChild(opcion("x", "bi-twitter-x", "X", e.x));
    rejilla.appendChild(opcion("telegram", "bi-telegram", "Telegram", e.telegram));
    rejilla.appendChild(opcion("correo", "bi-envelope", "Correo", e.correo));
    rejilla.appendChild(opcion("copiar", "bi-link-45deg", "Copiar enlace", null));
    menu.appendChild(rejilla);

    if (navigator.share) {
      var mas = document.createElement("button");
      mas.type = "button";
      mas.className = "menu-compartir__mas";
      mas.dataset.opcion = "mas";
      mas.innerHTML = '<i class="bi bi-three-dots" aria-hidden="true"></i><span><strong>Más opciones</strong>' +
        "<small>TikTok, Instagram, Messenger… (si están instalados)</small></span>";
      menu.appendChild(mas);
    }

    menu.addEventListener("click", function (evento) {
      var el = evento.target.closest("[data-opcion]");
      if (!el) return;
      var tipo = el.dataset.opcion;
      if (tipo === "copiar") {
        cerrarMenu(true);
        copiar(d.url);
      } else if (tipo === "mas") {
        cerrarMenu(true);
        navigator.share({ title: d.titulo, text: d.texto, url: d.url }).catch(function (error) {
          if (error && error.name !== "AbortError") copiar(d.url);  // cerrar el menú no es un error
        });
      } else {
        // Los enlaces se abren solos (pestaña nueva o la app de correo); solo se cierra la ventanita.
        setTimeout(function () { cerrarMenu(false); }, 0);
      }
    });
    menu.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape") { evento.preventDefault(); cerrarMenu(true); }
    });

    if (esComputadora()) {
      document.body.appendChild(menu);
      ubicar(menu, boton);
    } else {
      // En el celular sale desde abajo, a todo el ancho (como el menú de compartir del teléfono).
      menu.classList.add("menu-compartir--abajo");
      var cancelar = document.createElement("button");
      cancelar.type = "button";
      cancelar.className = "btn btn-outline-secondary w-100 mt-2";
      cancelar.textContent = "Cancelar";
      cancelar.addEventListener("click", function () { cerrarMenu(true); });
      menu.appendChild(cancelar);
      document.body.appendChild(menu);
    }
    menu.querySelector("[data-opcion]").focus({ preventScroll: true });
  }

  document.addEventListener("click", function (evento) {
    var boton = evento.target.closest ? evento.target.closest("[data-compartir]") : null;
    if (menu && !menu.contains(evento.target) && boton !== botonActual) cerrarMenu(false);
    if (!boton) return;
    if (menu && boton === botonActual) { cerrarMenu(false); return; }  // segundo clic: se cierra
    mostrarMenu(boton);
  });

  window.addEventListener("resize", function () { if (esComputadora()) cerrarMenu(false); });
  document.addEventListener("scroll", function (evento) {
    // En la PC la ventanita va pegada al botón: si la página se mueve, se cierra. En el celular va fija abajo.
    if (menu && esComputadora() && !menu.contains(evento.target)) cerrarMenu(false);
  }, true);

  // Para pruebas.
  window.NexalysCompartir = { enlaces: enlaces };
})();
