/*
 * Lista con buscador para los <select> que tienen el atributo data-buscable
 * (categoría y marca en el formulario de producto).
 *
 * Al hacer clic se abre la lista con un campo arriba: escribes "so" y quedan
 * Sony, Soundcore… Funciona sin tildes, con las flechas ↑ ↓, Enter y Esc.
 * Primero aparecen los nombres que EMPIEZAN con lo escrito y luego los que lo contienen.
 * El <select> original sigue en la página (oculto) y es el que se envía al guardar,
 * así que si el navegador no tiene JavaScript, el formulario funciona igual.
 */
(function () {
  "use strict";

  function normalizar(texto) {
    return (texto || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
  }

  var contador = 0;

  function crear(select) {
    contador += 1;
    var id = "lista-buscable-" + contador;
    var opciones = Array.prototype.filter.call(select.options, function (o) { return o.value !== ""; });
    var textoVacio = select.options.length && select.options[0].value === "" ? select.options[0].text : "Selecciona";

    var caja = document.createElement("div");
    caja.className = "lista-buscable";

    var boton = document.createElement("button");
    boton.type = "button";
    boton.id = id + "-boton";
    boton.className = "form-select lista-buscable__boton" + (select.classList.contains("is-invalid") ? " is-invalid" : "");
    boton.setAttribute("aria-haspopup", "listbox");
    boton.setAttribute("aria-expanded", "false");

    var panel = document.createElement("div");
    panel.className = "lista-buscable__panel";
    panel.hidden = true;

    var buscar = document.createElement("input");
    buscar.type = "search";
    buscar.className = "form-control form-control-sm lista-buscable__buscar";
    buscar.placeholder = select.dataset.buscable || "Escribe para buscar…";
    buscar.setAttribute("autocomplete", "off");
    buscar.setAttribute("role", "combobox");
    buscar.setAttribute("aria-autocomplete", "list");
    buscar.setAttribute("aria-controls", id + "-opciones");
    buscar.setAttribute("aria-expanded", "true");

    var lista = document.createElement("ul");
    lista.className = "lista-buscable__opciones";
    lista.id = id + "-opciones";
    lista.setAttribute("role", "listbox");

    var vacio = document.createElement("div");
    vacio.className = "lista-buscable__vacio";
    vacio.hidden = true;

    panel.append(buscar, lista, vacio);
    caja.append(boton, panel);
    select.insertAdjacentElement("afterend", caja);

    // El <select> queda oculto pero en el formulario.
    select.classList.add("visually-hidden");
    select.setAttribute("tabindex", "-1");
    select.setAttribute("aria-hidden", "true");

    // La etiqueta ("Marca *") ahora lleva al botón.
    var etiqueta = select.id && document.querySelector('label[for="' + select.id + '"]');
    if (etiqueta) {
      etiqueta.htmlFor = boton.id;
      if (!etiqueta.id) etiqueta.id = id + "-etiqueta";
      lista.setAttribute("aria-labelledby", etiqueta.id);
    }

    var visibles = [];
    var activa = -1;

    function mostrarElegida() {
      var elegida = select.options[select.selectedIndex];
      var tiene = elegida && elegida.value !== "";
      boton.textContent = tiene ? elegida.text : textoVacio;
      boton.classList.toggle("lista-buscable__boton--vacio", !tiene);
    }

    function marcarActiva(indice) {
      activa = indice;
      Array.prototype.forEach.call(lista.children, function (li, i) {
        var esta = i === indice;
        li.classList.toggle("activa", esta);
        if (esta) {
          buscar.setAttribute("aria-activedescendant", li.id);
          li.scrollIntoView({ block: "nearest" });
        }
      });
      if (indice < 0) buscar.removeAttribute("aria-activedescendant");
    }

    function filtrar() {
      var q = normalizar(buscar.value);
      var empiezan = [], contienen = [];
      opciones.forEach(function (o) {
        var n = normalizar(o.text);
        if (!q || n.indexOf(q) === 0) empiezan.push(o);
        else if (n.indexOf(q) !== -1 || n.split(/[\s()\-]+/).some(function (p) { return p.indexOf(q) === 0; })) contienen.push(o);
      });
      visibles = empiezan.concat(contienen);
      lista.textContent = "";
      visibles.forEach(function (o, i) {
        var li = document.createElement("li");
        li.id = id + "-op-" + i;
        li.setAttribute("role", "option");
        li.setAttribute("aria-selected", o.selected ? "true" : "false");
        li.textContent = o.text;
        if (o.selected) li.classList.add("elegida");
        li.addEventListener("mousedown", function (e) { e.preventDefault(); elegir(o); });
        lista.appendChild(li);
      });
      vacio.hidden = visibles.length > 0;
      vacio.textContent = "Ninguna coincide con «" + buscar.value.trim() + "»";
      var indiceElegida = visibles.findIndex(function (o) { return o.selected; });
      marcarActiva(q ? (visibles.length ? 0 : -1) : indiceElegida);
    }

    function abrir(textoInicial) {
      panel.hidden = false;
      boton.setAttribute("aria-expanded", "true");
      buscar.value = textoInicial || "";
      filtrar();
      buscar.focus();
    }

    function cerrar(volverAlBoton) {
      if (panel.hidden) return;
      panel.hidden = true;
      boton.setAttribute("aria-expanded", "false");
      if (volverAlBoton) boton.focus();
    }

    function elegir(opcion) {
      select.value = opcion.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      mostrarElegida();
      boton.classList.remove("is-invalid");
      cerrar(true);
    }

    boton.addEventListener("click", function () {
      if (panel.hidden) abrir(""); else cerrar(true);
    });
    // Si escribes una letra con el botón enfocado, se abre ya buscando esa letra.
    boton.addEventListener("keydown", function (e) {
      if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); abrir(e.key); }
      else if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") { e.preventDefault(); abrir(""); }
    });

    buscar.addEventListener("input", filtrar);
    buscar.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); if (visibles.length) marcarActiva(Math.min(activa + 1, visibles.length - 1)); }
      else if (e.key === "ArrowUp") { e.preventDefault(); if (visibles.length) marcarActiva(Math.max(activa - 1, 0)); }
      else if (e.key === "Enter") { e.preventDefault(); if (activa >= 0 && visibles[activa]) elegir(visibles[activa]); }
      else if (e.key === "Escape") { e.preventDefault(); cerrar(true); }
      else if (e.key === "Tab") { cerrar(false); }
    });

    document.addEventListener("mousedown", function (e) {
      if (!caja.contains(e.target)) cerrar(false);
    });

    select.addEventListener("change", mostrarElegida);
    mostrarElegida();
  }

  document.querySelectorAll("select[data-buscable]").forEach(crear);
})();
