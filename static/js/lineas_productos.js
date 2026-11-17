/*
 * Filas de productos de «Nuevo ingreso» y «Nueva venta» (<form data-lineas>, filas [data-linea]).
 *
 * - Producto repetido: si se elige un producto que ya está en otra fila, se suma la cantidad en esa fila,
 *   se limpia la fila nueva y se avisa («Ya estaba en la fila 1: sumamos 2 unidades»).
 *   El servidor también rechaza el mismo producto en dos filas (inventario/forms.py, BaseLineas).
 * - Al recuperar un borrador (static/js/no_perder.js) se muestran las filas que tienen producto y, si se
 *   volvió de «+ Crear producto» (?producto=ID), el producto nuevo entra en la primera fila libre.
 */
(function () {
  "use strict";

  function iniciar(form) {
    var filas = Array.prototype.slice.call(form.querySelectorAll("[data-linea]"));
    var selectDe = function (fila) { return fila.querySelector("select"); };
    var cantidadDe = function (fila) { return fila.querySelector("input[name$='-cantidad']"); };

    function avisar(fila, texto) {
      var previo = fila.querySelector(".aviso-repetido");
      if (previo) previo.remove();
      var aviso = document.createElement("div");
      aviso.className = "aviso-repetido";
      aviso.setAttribute("role", "status");
      aviso.innerHTML = '<i class="bi bi-info-circle-fill" aria-hidden="true"></i> ';
      aviso.appendChild(document.createTextNode(texto));
      selectDe(fila).parentNode.appendChild(aviso);
      setTimeout(function () { aviso.remove(); }, 7000);
    }

    function limpiar(fila) {
      fila.querySelectorAll("input").forEach(function (c) { if (c.type !== "hidden") c.value = ""; });
      var select = selectDe(fila);
      select.value = "";
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }

    form.addEventListener("change", function (evento) {
      var select = evento.target;
      if (select.tagName !== "SELECT" || !select.value) return;
      var fila = select.closest("[data-linea]");
      if (!fila) return;
      var otra = filas.find(function (f) { return f !== fila && selectDe(f).value === select.value; });
      if (!otra) return;
      var cantidad = cantidadDe(fila), destino = cantidadDe(otra);
      var suma = parseInt(cantidad && cantidad.value, 10) || 1;
      destino.value = (parseInt(destino.value, 10) || 0) + suma;
      destino.dispatchEvent(new Event("input", { bubbles: true }));
      limpiar(fila);
      otra.classList.remove("d-none");
      avisar(otra, "Ese producto ya estaba en la fila " + (filas.indexOf(otra) + 1) + ": sumamos " + suma +
        (suma === 1 ? " unidad" : " unidades") + " aquí.");
      destino.focus();
    });

    form.addEventListener("borrador:restaurado", function () {
      filas.forEach(function (fila) { if (selectDe(fila).value) fila.classList.remove("d-none"); });
      var nuevo = new URLSearchParams(location.search).get("producto");
      if (!nuevo || filas.some(function (f) { return selectDe(f).value === nuevo; })) return;
      var libre = filas.find(function (f) { return !selectDe(f).value; });
      var select = libre && selectDe(libre);
      if (!select || !select.querySelector('option[value="' + CSS.escape(nuevo) + '"]')) return;
      libre.classList.remove("d-none");
      select.value = nuevo;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  document.querySelectorAll("form[data-lineas]").forEach(iniciar);
})();
