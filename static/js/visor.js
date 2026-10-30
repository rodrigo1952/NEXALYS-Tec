/*
 * Visor de imágenes (ventana #modal-imagen de base.html).
 *
 * Al hacer clic en una imagen con data-ampliar, se abre en grande. Las imágenes con el
 * mismo data-galeria (las fotos de un producto) se recorren con las flechas, las teclas ← → o
 * deslizando el dedo, y abajo se ven sus miniaturas. Al cerrar, la galería de la página queda
 * en la última foto vista. El fondo es claro y difuminado (estilos .visor en marca.css).
 */
(function () {
  var modal = document.getElementById("modal-imagen");
  var ampliada = document.getElementById("imagen-ampliada");
  var titulo = document.getElementById("modal-imagen-titulo");
  var contador = document.getElementById("visor-contador");
  var anterior = document.getElementById("visor-anterior");
  var siguiente = document.getElementById("visor-siguiente");
  var miniaturas = document.getElementById("visor-miniaturas");
  var grupo = [], actual = 0, inicioX = null;

  function dibujarMiniaturas() {
    miniaturas.innerHTML = "";
    miniaturas.classList.toggle("d-none", grupo.length < 2);
    if (grupo.length < 2) return;
    grupo.forEach(function (imagen, indice) {
      var boton = document.createElement("button");
      boton.type = "button";
      boton.className = "visor__miniatura";
      boton.setAttribute("aria-label", "Ver foto " + (indice + 1));
      var img = document.createElement("img");
      img.src = imagen.dataset.ampliar;
      img.alt = "";
      boton.appendChild(img);
      boton.addEventListener("click", function () { mostrar(indice); });
      miniaturas.appendChild(boton);
    });
  }

  function mostrar(indice) {
    actual = (indice + grupo.length) % grupo.length;
    var imagen = grupo[actual];
    ampliada.src = imagen.dataset.ampliar;
    ampliada.alt = imagen.alt || "";
    titulo.textContent = imagen.alt || "";
    var varias = grupo.length > 1;
    contador.textContent = varias ? (actual + 1) + " de " + grupo.length : "";
    anterior.classList.toggle("d-none", !varias);
    siguiente.classList.toggle("d-none", !varias);
    Array.prototype.forEach.call(miniaturas.children, function (boton, indice) {
      boton.classList.toggle("activa", indice === actual);
      if (indice === actual) boton.setAttribute("aria-current", "true"); else boton.removeAttribute("aria-current");
    });
  }

  document.addEventListener("click", function (evento) {
    var imagen = evento.target.closest("[data-ampliar]");
    if (!imagen) return;
    evento.preventDefault();
    grupo = imagen.dataset.galeria
      ? Array.prototype.slice.call(document.querySelectorAll('[data-ampliar][data-galeria="' + imagen.dataset.galeria + '"]'))
      : [imagen];
    dibujarMiniaturas();
    mostrar(grupo.indexOf(imagen));
    bootstrap.Modal.getOrCreateInstance(modal).show();
  });
  anterior.addEventListener("click", function () { mostrar(actual - 1); });
  siguiente.addEventListener("click", function () { mostrar(actual + 1); });
  document.addEventListener("keydown", function (evento) {
    if (!modal.classList.contains("show") || grupo.length < 2) return;
    if (evento.key === "ArrowLeft") { evento.preventDefault(); mostrar(actual - 1); }
    if (evento.key === "ArrowRight") { evento.preventDefault(); mostrar(actual + 1); }
  });
  ampliada.addEventListener("touchstart", function (evento) { inicioX = evento.touches[0].clientX; }, { passive: true });
  ampliada.addEventListener("touchend", function (evento) {
    if (inicioX === null || grupo.length < 2) return;
    var distancia = evento.changedTouches[0].clientX - inicioX;
    inicioX = null;
    if (Math.abs(distancia) > 50) mostrar(distancia < 0 ? actual + 1 : actual - 1);
  });
  modal.addEventListener("hidden.bs.modal", function () {
    var carrusel = grupo[actual] && grupo[actual].closest(".carousel");
    if (carrusel && grupo.length > 1) bootstrap.Carousel.getOrCreateInstance(carrusel).to(actual);
  });
})();
