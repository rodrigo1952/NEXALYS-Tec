/*
 * Botones de WhatsApp (producto, perfil de la tienda, favoritos y Tiendas cercanas).
 *
 * El servidor arma enlaces https://wa.me/51…?text=… :
 *   - En el CELULAR se dejan así: wa.me abre la app de WhatsApp directo en el chat.
 *   - En la COMPUTADORA, wa.me pasa por una página intermedia de WhatsApp. En su lugar, al hacer clic
 *     aparece un menú pequeño con dos opciones, ambas directo al chat y con el mensaje ya escrito:
 *       · «WhatsApp Web»: web.whatsapp.com/send en una pestaña nueva.
 *       · «App de WhatsApp»: whatsapp://send, abre la app de Windows (si está instalada), sin pestañas.
 *     La elección se puede recordar en ese navegador; luego un aviso con «Cambiar» permite elegir otra vez.
 *
 * No se puede reutilizar una pestaña de WhatsApp Web: WhatsApp y el navegador cortan el vínculo con la
 * pestaña que abre el sitio, así que cada consulta por la web abre una pestaña nueva.
 * Ctrl+clic, clic con la rueda o sin JavaScript: se usa el enlace wa.me de siempre.
 */
(function () {
  "use strict";

  var CLAVE = "nexalys_whatsapp_modo";  // "web" o "app"
  var menu = null, aviso = null, enlaceActual = null, temporizadorAviso = null;

  function esComputadora() {
    var ua = navigator.userAgent || "";
    if (navigator.userAgentData && navigator.userAgentData.mobile) return false;
    if (/Android|iPhone|iPad|iPod|Mobile|Silk|Kindle/i.test(ua)) return false;
    // iPad con iPadOS se presenta como Mac: se distingue porque tiene pantalla táctil.
    if (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) return false;
    return window.matchMedia ? window.matchMedia("(pointer: fine)").matches : true;
  }

  // https://wa.me/51987654321?text=Hola → { telefono: "51987654321", texto: "Hola" }
  function datos(enlaceWaMe) {
    var url;
    try { url = new URL(enlaceWaMe); } catch (e) { return null; }
    if (url.hostname !== "wa.me") return null;
    var telefono = url.pathname.replace(/\D/g, "");
    return telefono ? { telefono: telefono, texto: url.searchParams.get("text") || "" } : null;
  }

  function destino(modo, d) {
    var texto = d.texto ? "&text=" + encodeURIComponent(d.texto) : "";
    return (modo === "app" ? "whatsapp://send?phone=" : "https://web.whatsapp.com/send?phone=") + d.telefono + texto;
  }

  function leerModo() {
    try { return localStorage.getItem(CLAVE); } catch (e) { return null; }
  }

  function guardarModo(modo) {
    try {
      if (modo) localStorage.setItem(CLAVE, modo); else localStorage.removeItem(CLAVE);
    } catch (e) { /* navegación privada: no se recuerda */ }
  }

  function abrir(modo, d) {
    if (modo === "app") {
      window.location.href = destino("app", d);  // el navegador pregunta «¿Abrir WhatsApp?»
    } else {
      window.open(destino("web", d), "_blank", "noopener");
    }
  }

  // ---------- Menú ----------
  function cerrarMenu(devolverFoco) {
    if (!menu) return;
    menu.remove();
    menu = null;
    if (devolverFoco && enlaceActual) enlaceActual.focus();
  }

  function opcion(modo, icono, titulo, detalle) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "menu-whatsapp__opcion";
    b.dataset.modo = modo;
    b.innerHTML = '<i class="bi ' + icono + '" aria-hidden="true"></i><span><strong>' + titulo +
      "</strong><small>" + detalle + "</small></span>";
    return b;
  }

  function ubicar(caja, enlace) {
    var r = enlace.getBoundingClientRect(), margen = 8;
    var ancho = caja.offsetWidth, alto = caja.offsetHeight;
    var izquierda = Math.min(Math.max(margen, r.left), window.innerWidth - ancho - margen);
    var arriba = r.bottom + 6;
    if (arriba + alto > window.innerHeight - margen && r.top - alto - 6 > margen) arriba = r.top - alto - 6;
    caja.style.left = izquierda + "px";
    caja.style.top = Math.max(margen, arriba) + "px";
  }

  function mostrarMenu(enlace, d) {
    cerrarMenu(false);
    cerrarAviso();
    enlaceActual = enlace;
    menu = document.createElement("div");
    menu.className = "menu-whatsapp";
    menu.setAttribute("role", "dialog");
    menu.setAttribute("aria-label", "Abrir el chat de WhatsApp");
    menu.innerHTML = '<p class="menu-whatsapp__titulo">¿Dónde abrir el chat?</p>';
    menu.appendChild(opcion("web", "bi-globe2", "WhatsApp Web", "En una pestaña nueva del navegador"));
    menu.appendChild(opcion("app", "bi-laptop", "App de WhatsApp", "Si la tienes instalada en tu computadora"));
    var recordar = document.createElement("label");
    recordar.className = "menu-whatsapp__recordar";
    recordar.innerHTML = '<input type="checkbox" class="form-check-input" checked> Recordar mi elección en este navegador';
    menu.appendChild(recordar);

    menu.addEventListener("click", function (evento) {
      var boton = evento.target.closest(".menu-whatsapp__opcion");
      if (!boton) return;
      var modo = boton.dataset.modo;
      var recordado = recordar.querySelector("input").checked;
      if (recordado) guardarModo(modo);
      cerrarMenu(false);
      abrir(modo, d);
      if (modo === "app") mostrarAviso(enlace, d, "app", recordado);
    });
    menu.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape") { evento.preventDefault(); cerrarMenu(true); }
    });

    document.body.appendChild(menu);
    ubicar(menu, enlace);
    menu.querySelector(".menu-whatsapp__opcion").focus();
  }

  // ---------- Aviso (cuando se usó la elección recordada o se abrió la app) ----------
  function cerrarAviso() {
    clearTimeout(temporizadorAviso);
    if (aviso) { aviso.remove(); aviso = null; }
  }

  function mostrarAviso(enlace, d, modo, recordado) {
    cerrarAviso();
    aviso = document.createElement("div");
    aviso.className = "aviso-whatsapp";
    aviso.setAttribute("role", "status");
    var texto = modo === "app"
      ? "Abriendo la app de WhatsApp… Si no se abrió, puede que no esté instalada."
      : "Se abrió WhatsApp Web en una pestaña nueva.";
    aviso.innerHTML = '<i class="bi bi-whatsapp" aria-hidden="true"></i><span>' + texto + "</span>";
    if (modo === "app") {
      var web = document.createElement("button");
      web.type = "button";
      web.className = "btn btn-link btn-sm p-0";
      web.textContent = "Usar WhatsApp Web";
      web.addEventListener("click", function () {
        if (recordado) guardarModo("web");
        cerrarAviso();
        abrir("web", d);
      });
      aviso.appendChild(web);
    }
    if (recordado) {
      var cambiar = document.createElement("button");
      cambiar.type = "button";
      cambiar.className = "btn btn-link btn-sm p-0";
      cambiar.textContent = "Cambiar";
      cambiar.addEventListener("click", function (evento) {
        evento.stopPropagation();  // si no, el clic llega al documento y cierra el menú recién abierto
        guardarModo(null);
        mostrarMenu(enlace, d);
      });
      aviso.appendChild(cambiar);
    }
    var cerrar = document.createElement("button");
    cerrar.type = "button";
    cerrar.className = "btn-close btn-sm";
    cerrar.setAttribute("aria-label", "Cerrar aviso");
    cerrar.addEventListener("click", cerrarAviso);
    aviso.appendChild(cerrar);
    document.body.appendChild(aviso);
    temporizadorAviso = setTimeout(cerrarAviso, 9000);
  }

  if (!esComputadora()) {
    window.NexalysWhatsApp = { datos: datos, destino: destino };
    return;
  }

  document.addEventListener("click", function (evento) {
    if (menu && !menu.contains(evento.target)) cerrarMenu(false);
    if (evento.defaultPrevented || evento.button !== 0) return;
    if (evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey) return;
    var enlace = evento.target.closest ? evento.target.closest('a[href^="https://wa.me/"]') : null;
    if (!enlace) return;
    var d = datos(enlace.href);
    if (!d) return;
    evento.preventDefault();
    var modo = leerModo();
    if (modo === "web" || modo === "app") {
      abrir(modo, d);
      mostrarAviso(enlace, d, modo, true);
    } else {
      mostrarMenu(enlace, d);
    }
  });

  window.addEventListener("resize", function () { cerrarMenu(false); });
  document.addEventListener("scroll", function () { cerrarMenu(false); }, true);

  // Para pruebas.
  window.NexalysWhatsApp = { datos: datos, destino: destino };
})();
