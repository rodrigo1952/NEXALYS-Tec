// Ayudas para todos los formularios de la página (se carga en base.html):
//   1. Contraseña para datos sensibles (templates/_confirmar_clave.html): aparece encima del
//      botón «Guardar cambios» apenas cambias el nombre, la dirección, el WhatsApp, la
//      ubicación o el correo, y dice qué cambiaste. Si intentas guardar sin escribirla,
//      no se envía: la página baja hasta ella y la resalta.
//   2. Si el formulario vuelve con errores, la página baja hasta el primero y lo resalta
//      (antes se quedaba arriba y parecía que todo se había guardado).
(function () {
  "use strict";

  var RESALTADO = "campo-resaltado";
  var suave = !(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  // Baja hasta el elemento, lo resalta un momento y pone el cursor en su campo.
  function resaltar(caja, campo) {
    caja.scrollIntoView({ behavior: suave ? "smooth" : "auto", block: "center" });
    caja.classList.remove(RESALTADO);
    void caja.offsetWidth;  // reinicia la animación si ya estaba resaltado
    caja.classList.add(RESALTADO);
    setTimeout(function () { caja.classList.remove(RESALTADO); }, 2600);
    if (campo) {
      try { campo.focus({ preventScroll: true }); } catch (e) { campo.focus(); }
    }
  }

  // =================== 1. Contraseña para datos sensibles ===================
  function normalizar(tipo, valor) {
    valor = String(valor == null ? "" : valor).replace(/\s+/g, " ").trim();
    if (tipo === "correo") return valor.toLowerCase();
    if (tipo === "telefono") {
      valor = valor.replace(/[\s\-()]/g, "");
      if (valor.indexOf("+51") === 0) valor = valor.slice(3);
      else if (valor.indexOf("51") === 0 && valor.length === 11) valor = valor.slice(2);
      return valor;
    }
    if (tipo === "numero") {
      var numero = parseFloat(valor.replace(",", "."));
      return valor === "" || isNaN(numero) ? valor : numero.toFixed(6);
    }
    return valor;
  }

  function unir(nombres) {
    if (nombres.length < 2) return nombres.join("");
    return nombres.slice(0, -1).join(", ") + " y " + nombres[nombres.length - 1];
  }

  function confirmarClave(caja) {
    var form = caja.closest("form");
    if (!form) return;
    var campo = caja.querySelector("input[type=password]");
    var motivo = caja.querySelector("[data-motivo-clave]");
    var error = caja.querySelector("[data-error-clave]");
    var sensibles = form.querySelectorAll("[data-sensible]");

    // Sin JavaScript se ve la ayuda larga; con JavaScript, el motivo exacto y una ayuda corta.
    caja.querySelector("[data-ayuda-clave]").hidden = true;
    caja.querySelector("[data-ayuda-clave-corta]").hidden = false;

    function cambiados() {
      var nombres = [];
      Array.prototype.forEach.call(sensibles, function (el) {
        var tipo = el.dataset.sensibleTipo;
        if (normalizar(tipo, el.value) !== normalizar(tipo, el.dataset.sensibleOriginal) &&
            nombres.indexOf(el.dataset.sensible) === -1) {
          nombres.push(el.dataset.sensible);
        }
      });
      return nombres;
    }

    // Si el servidor ya pidió la contraseña, la caja se queda a la vista aunque aquí no se note el cambio.
    var pedidaPorElServidor = caja.classList.contains("confirmar-clave--error");

    function actualizar() {
      var nombres = cambiados();
      var estaba = !caja.hidden;
      caja.hidden = !nombres.length && !pedidaPorElServidor;
      if (!nombres.length) return;
      motivo.textContent = "";
      motivo.appendChild(document.createTextNode("Cambiaste: "));
      var fuerte = document.createElement("strong");
      fuerte.textContent = unir(nombres);
      motivo.appendChild(fuerte);
      motivo.appendChild(document.createTextNode(". Por seguridad, escribe tu contraseña para guardar."));
      // Recién apareció: se resalta un instante (sin mover la página) para que se note.
      if (!estaba) {
        caja.classList.remove("confirmar-clave--aparece");
        void caja.offsetWidth;
        caja.classList.add("confirmar-clave--aparece");
      }
    }

    form.addEventListener("input", actualizar);
    form.addEventListener("change", actualizar);
    form.addEventListener("borrador:restaurado", actualizar);
    campo.addEventListener("input", function () {
      if (campo.value) { error.hidden = true; caja.classList.remove("confirmar-clave--error"); }
    });

    // Se registra en «captura» para ir antes que el «Procesando…» de base.html y que no_perder.js.
    document.addEventListener("submit", function (evento) {
      if (evento.target !== form || caja.hidden || campo.value) return;
      evento.preventDefault();
      evento.stopPropagation();
      error.textContent = "Escribe tu contraseña actual para guardar estos cambios.";
      error.hidden = false;
      caja.classList.add("confirmar-clave--error");
      resaltar(caja, campo);
    }, true);

    actualizar();
  }

  // =================== 2. Bajar hasta el primer error ===================
  function visible(el) {
    return !el.hidden && el.offsetParent !== null && el.textContent.trim() !== "";
  }

  function primerError() {
    // Solo cuando la página es la respuesta a un envío (POST) que volvió con errores (base.html).
    if (!document.body.hasAttribute("data-formulario-enviado")) return;
    // Mensajes de error que dibujan las plantillas: debajo de cada campo o arriba del formulario.
    var errores = document.querySelectorAll(
      "form div.text-danger.small, form .alert-danger, form .invalid-feedback, form .errorlist");
    var primero = Array.prototype.filter.call(errores, visible)[0];
    if (!primero) return;
    // La caja del campo: la de la contraseña o el bloque que tiene la etiqueta y el campo.
    var caja = primero.closest("[data-confirmar-clave]") ||
      (primero.classList.contains("alert") ? primero : primero.parentElement);
    var campo = primero.classList.contains("alert") ? null :
      caja.querySelector("input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea");
    resaltar(caja, campo);
  }

  document.querySelectorAll("[data-confirmar-clave]").forEach(confirmarClave);
  // Se espera a que la página termine de acomodarse (fotos, mapa) antes de bajar.
  if (document.readyState === "complete") primerError();
  else window.addEventListener("load", primerError, { once: true });

  window.NexalysFormularios = { resaltar: resaltar };
})();
