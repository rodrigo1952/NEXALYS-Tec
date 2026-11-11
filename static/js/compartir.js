/*
 * Botón «Compartir» (templates/_compartir.html).
 *  - Celular o tablet (pantalla táctil): abre el menú de compartir del teléfono.
 *  - PC: copia el enlace y muestra «Enlace copiado».
 */
(function () {
  "use strict";

  var esTactil = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;

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
    var listo = function () { avisar("Enlace copiado. Pégalo en WhatsApp, Facebook o donde quieras compartirlo."); };
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

  document.addEventListener("click", function (evento) {
    var boton = evento.target.closest("[data-compartir]");
    if (!boton) return;
    var datos = { title: boton.dataset.titulo, text: boton.dataset.texto, url: boton.dataset.url };
    if (esTactil && navigator.share) {
      navigator.share(datos).catch(function (error) {
        if (error && error.name !== "AbortError") copiar(datos.url);  // cerrar el menú no es un error
      });
      return;
    }
    copiar(datos.url);
  });
})();
