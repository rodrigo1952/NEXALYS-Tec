// Color de la etiqueta de una marca (consola del administrador, nov 2026):
// al elegir el color o escribir el nombre, la vista previa de la etiqueta cambia y se avisa si el
// nombre en blanco se leería bien (contraste de al menos 4.5 : 1). El servidor vuelve a revisarlo al guardar.
(function () {
  "use strict";

  var MINIMO = 4.5;

  function canal(valor) {
    valor = valor / 255;
    return valor <= 0.03928 ? valor / 12.92 : Math.pow((valor + 0.055) / 1.055, 2.4);
  }

  function contrasteConBlanco(color) {
    var rojo = parseInt(color.substr(1, 2), 16);
    var verde = parseInt(color.substr(3, 2), 16);
    var azul = parseInt(color.substr(5, 2), 16);
    var luz = 0.2126 * canal(rojo) + 0.7152 * canal(verde) + 0.0722 * canal(azul);
    return 1.05 / (luz + 0.05);
  }

  document.querySelectorAll("[data-selector-color]").forEach(function (caja) {
    var campo = caja.querySelector("input[type=color]");
    var vista = caja.querySelector("[data-vista-marca]");
    var aviso = caja.querySelector("[data-contraste]");
    var nombre = campo.form ? campo.form.querySelector("[name=nombre]") : null;
    if (!campo || !vista || !aviso) return;

    function actualizar() {
      var color = campo.value || "#0B1B3A";
      var texto = nombre && nombre.value.trim() ? nombre.value.trim() : "Vista previa";
      vista.style.setProperty("--chip-marca", color);
      vista.textContent = texto;
      var contraste = contrasteConBlanco(color);
      var valor = contraste.toFixed(1) + " : 1";
      var bien = contraste >= MINIMO;
      aviso.classList.toggle("selector-color__contraste--bien", bien);
      aviso.classList.toggle("selector-color__contraste--mal", !bien);
      aviso.innerHTML = "";
      var icono = document.createElement("i");
      icono.className = "bi " + (bien ? "bi-check-circle-fill" : "bi-exclamation-triangle-fill");
      icono.setAttribute("aria-hidden", "true");
      aviso.appendChild(icono);
      aviso.appendChild(document.createTextNode(
        bien ? " Se lee bien (contraste " + valor + ")"
             : " No se lee bien (contraste " + valor + "; mínimo 4.5 : 1). Elige un tono más oscuro."
      ));
    }

    campo.addEventListener("input", actualizar);
    if (nombre) nombre.addEventListener("input", actualizar);
    actualizar();
  });
})();
