/*
 * Campo del logo de la tienda (templates/tiendas/_campo_logo.html), con el mismo trato que las fotos de
 * los productos: clic en el círculo (o «Cambiar logo») para elegir, o arrastrar y soltar una imagen.
 * La vista previa se ve al instante; nada se guarda hasta enviar el formulario.
 *   - «Quitar logo» marca la casilla para quitarlo al guardar (o, en la ventana del menú, lo quita al tocarlo).
 *   - «Deshacer» vuelve al logo que había.
 * Si el formulario tiene un botón [data-logo-guardar], se activa solo cuando hay una imagen nueva.
 */
(function () {
  "use strict";
  var TIPOS = /^image\/(jpeg|png|webp)$/;
  var MAXIMO = 2 * 1024 * 1024;

  function iniciar(campo) {
    if (campo.dataset.listo) return;  // el script puede estar dos veces en la página
    campo.dataset.listo = "1";
    var archivo = campo.querySelector("[data-logo-archivo]");
    var circulo = campo.querySelector("[data-logo-elegir]");
    var vista = campo.querySelector("[data-logo-vista]");
    var inicial = campo.querySelector("[data-logo-inicial]");
    var estado = campo.querySelector("[data-logo-estado]");
    var cambiar = campo.querySelector("[data-logo-cambiar]");
    var quitar = campo.querySelector("[data-logo-quitar]");
    var deshacer = campo.querySelector("[data-logo-deshacer]");
    var limpiar = campo.querySelector("[data-logo-limpiar]");
    var formulario = campo.closest("form");
    var guardar = formulario ? formulario.querySelector("[data-logo-guardar]") : null;
    var original = vista.getAttribute("src") || "";
    var urlTemporal = null;

    function pintar(src, texto, clase) {
      if (urlTemporal && src !== urlTemporal) { URL.revokeObjectURL(urlTemporal); urlTemporal = null; }
      vista.hidden = !src;
      if (src) vista.src = src; else vista.removeAttribute("src");
      inicial.hidden = !!src;
      circulo.classList.toggle("campo-logo__circulo--vacio", !src);
      estado.className = "campo-logo__estado" + (clase ? " " + clase : "");
      estado.textContent = texto || "";
      var cambio = !!texto && clase !== "text-danger";
      deshacer.hidden = !cambio;
      if (quitar) quitar.hidden = cambio && limpiar && limpiar.checked;
      if (guardar) guardar.disabled = !(archivo.files && archivo.files.length);
    }

    function usar(imagen) {
      if (!TIPOS.test(imagen.type)) { pintar(vista.hidden ? "" : vista.src, "Elige una imagen JPG, PNG o WEBP.", "text-danger"); return false; }
      if (imagen.size > MAXIMO) { pintar(vista.hidden ? "" : vista.src, "La imagen pesa más de 2 MB. Elige una más liviana.", "text-danger"); return false; }
      if (limpiar) limpiar.checked = false;
      if (urlTemporal) URL.revokeObjectURL(urlTemporal);
      urlTemporal = URL.createObjectURL(imagen);
      pintar(urlTemporal, "Logo nuevo: «" + imagen.name + "». Se guardará al presionar «" + (guardar ? "Guardar logo" : "Guardar cambios") + "».", "text-success");
      return true;
    }

    function elegir() { archivo.click(); }
    circulo.addEventListener("click", elegir);
    cambiar.addEventListener("click", elegir);
    archivo.addEventListener("change", function () {
      if (archivo.files.length && !usar(archivo.files[0])) archivo.value = "";
    });

    if (quitar && limpiar) {
      quitar.addEventListener("click", function () {
        archivo.value = "";
        limpiar.checked = true;
        pintar("", "El logo se quitará al presionar «Guardar cambios».", "text-warning-emphasis");
      });
    }
    deshacer.addEventListener("click", function () {
      archivo.value = "";
      if (limpiar) limpiar.checked = false;
      pintar(original, "", "");
    });

    // Arrastrar y soltar una imagen sobre el campo.
    ["dragenter", "dragover"].forEach(function (tipo) {
      campo.addEventListener(tipo, function (evento) {
        if (!evento.dataTransfer || Array.prototype.indexOf.call(evento.dataTransfer.types, "Files") === -1) return;
        evento.preventDefault();
        campo.classList.add("campo-logo--soltar");
      });
    });
    ["dragleave", "drop"].forEach(function (tipo) {
      campo.addEventListener(tipo, function (evento) {
        if (tipo === "dragleave" && campo.contains(evento.relatedTarget)) return;
        campo.classList.remove("campo-logo--soltar");
      });
    });
    campo.addEventListener("drop", function (evento) {
      if (!evento.dataTransfer || !evento.dataTransfer.files.length) return;
      evento.preventDefault();
      var imagen = evento.dataTransfer.files[0];
      if (!usar(imagen)) return;
      var transferencia = new DataTransfer();
      transferencia.items.add(imagen);
      archivo.files = transferencia.files;
      if (guardar) guardar.disabled = false;
    });

    pintar(original, "", "");
    campo.reiniciarLogo = function () { archivo.value = ""; if (limpiar) limpiar.checked = false; pintar(original, "", ""); };
  }

  document.querySelectorAll("[data-campo-logo]").forEach(iniciar);
})();
