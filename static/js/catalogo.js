/*
 * Catálogo: filtros que se aplican al instante, deslizador de precio y forma de ver los productos.
 *
 * - En computadora, marcar una opción o soltar el deslizador recarga la lista con ese filtro.
 *   En el celular (panel «Filtrar») se eligen varias cosas y luego se toca «Ver resultados».
 * - «Ordenar por» siempre se aplica al instante.
 * - La vista (4 por fila, 3 por fila o lista) se recuerda en este navegador.
 * Sin JavaScript todo sigue funcionando con el botón «Ver resultados».
 */
(function () {
  "use strict";
  var form = document.getElementById("filtros-catalogo");
  if (!form) return;
  var escritorio = window.matchMedia("(min-width: 992px)");
  form.classList.add("filtros--auto");

  function enviar() {
    if (form.requestSubmit) form.requestSubmit(); else form.submit();
  }

  // Los campos vacíos no se envían: así la dirección queda limpia (?marca=3 en vez de ?precio_min=&...).
  form.addEventListener("submit", function () {
    document.querySelectorAll("[data-precio-desde], [data-precio-hasta], [data-orden]").forEach(function (campo) {
      if (!campo.value) campo.disabled = true;
    });
  });

  // Al volver con «Atrás», el navegador puede mostrar la página guardada: se reactivan los campos.
  window.addEventListener("pageshow", function () {
    document.querySelectorAll("[data-precio-desde], [data-precio-hasta], [data-orden]").forEach(function (campo) { campo.disabled = false; });
  });

  form.addEventListener("change", function (evento) {
    if (evento.target.matches("[data-desde], [data-hasta]")) return;  // el deslizador se envía al soltarlo
    if (escritorio.matches) enviar();
  });

  var orden = document.querySelector("[data-orden]");
  if (orden) orden.addEventListener("change", enviar);

  // ---- Deslizador de precio (dos controles sobre la misma pista) ----
  var rango = form.querySelector("[data-rango]");
  if (rango) {
    var minimo = parseFloat(rango.dataset.minimo);
    var maximo = parseFloat(rango.dataset.maximo);
    var desde = rango.querySelector("[data-desde]");
    var hasta = rango.querySelector("[data-hasta]");
    var relleno = rango.querySelector("[data-relleno]");
    var numeroDesde = form.querySelector("[data-precio-desde]");
    var numeroHasta = form.querySelector("[data-precio-hasta]");

    var pintar = function () {
      var a = (parseFloat(desde.value) - minimo) / (maximo - minimo) * 100;
      var b = (parseFloat(hasta.value) - minimo) / (maximo - minimo) * 100;
      relleno.style.left = a + "%";
      relleno.style.right = (100 - b) + "%";
    };

    desde.addEventListener("input", function () {
      if (parseFloat(desde.value) > parseFloat(hasta.value)) desde.value = hasta.value;
      numeroDesde.value = parseFloat(desde.value) <= minimo ? "" : desde.value;
      pintar();
    });
    hasta.addEventListener("input", function () {
      if (parseFloat(hasta.value) < parseFloat(desde.value)) hasta.value = desde.value;
      numeroHasta.value = parseFloat(hasta.value) >= maximo ? "" : hasta.value;
      pintar();
    });
    [desde, hasta].forEach(function (control) {
      control.addEventListener("change", function () { if (escritorio.matches) enviar(); });
    });
    numeroDesde.addEventListener("input", function () { desde.value = numeroDesde.value || minimo; pintar(); });
    numeroHasta.addEventListener("input", function () { hasta.value = numeroHasta.value || maximo; pintar(); });
    pintar();
  }

  // ---- «Ver todas» las marcas ----
  form.querySelectorAll("[data-ver-mas]").forEach(function (boton) {
    var texto = boton.textContent;
    boton.addEventListener("click", function () {
      var abierto = boton.getAttribute("aria-expanded") === "true";
      boton.closest("details").querySelectorAll(".filtro__extra").forEach(function (fila) {
        fila.classList.toggle("d-none", abierto);
      });
      boton.setAttribute("aria-expanded", String(!abierto));
      boton.textContent = abierto ? texto : "Ver menos";
    });
  });

  // ---- Vista: 4 por fila, 3 por fila o lista (se recuerda en este navegador) ----
  var grilla = document.getElementById("grilla-catalogo");
  var botones = document.querySelectorAll("[data-vista-boton]");
  function elegirVista(vista) {
    if (grilla) grilla.dataset.vista = vista;
    botones.forEach(function (boton) {
      var activo = boton.dataset.vistaBoton === vista;
      boton.classList.toggle("activo", activo);
      boton.setAttribute("aria-pressed", String(activo));
    });
  }
  var guardada = null;
  try { guardada = window.localStorage.getItem("nx-vista-catalogo"); } catch (e) { guardada = null; }
  elegirVista(["4", "3", "lista"].indexOf(guardada) >= 0 ? guardada : "3");
  botones.forEach(function (boton) {
    boton.addEventListener("click", function () {
      elegirVista(boton.dataset.vistaBoton);
      try { window.localStorage.setItem("nx-vista-catalogo", boton.dataset.vistaBoton); } catch (e) { /* sin almacenamiento */ }
    });
  });
})();
