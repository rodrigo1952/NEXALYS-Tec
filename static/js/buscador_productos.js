/*
 * Buscador de productos para las listas <select class="buscador-producto">
 * (Nuevo ingreso, Nueva venta y Nuevo ajuste).
 *
 * El <select> original se queda en la página (oculto) y es el que se envía al
 * guardar: este archivo solo agrega una caja de texto encima para buscar. Si el
 * JavaScript no carga, se sigue viendo la lista normal y todo funciona igual.
 *
 * - Busca por nombre, código, marca y categoría (palabras en cualquier orden,
 *   sin importar mayúsculas ni tildes).
 * - Flechas ↑ ↓ para moverse, Enter para elegir, Esc para cerrar.
 * - Lector de código de barras: escribe el código y presiona Enter; si el código
 *   coincide exactamente con un producto, se elige solo.
 */
(function () {
  "use strict";

  const MAX_RESULTADOS = 50;
  const normalizar = (texto) =>
    texto.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();

  let contador = 0;

  function crearBuscador(select) {
    contador += 1;
    const idLista = `buscador-lista-${contador}`;
    const opciones = Array.from(select.options).filter((o) => o.value !== "");
    const vacio = Array.from(select.options).find((o) => o.value === "");

    const caja = document.createElement("div");
    caja.className = "buscador-producto-caja position-relative";

    const entrada = document.createElement("input");
    entrada.type = "text";
    entrada.className = "form-control buscador-producto-input";
    entrada.placeholder = (vacio ? vacio.text : "Elige un producto") + " (escribe para buscar)";
    entrada.autocomplete = "off";
    entrada.setAttribute("role", "combobox");
    entrada.setAttribute("aria-autocomplete", "list");
    entrada.setAttribute("aria-expanded", "false");
    entrada.setAttribute("aria-controls", idLista);
    if (select.classList.contains("is-invalid")) entrada.classList.add("is-invalid");

    const lista = document.createElement("ul");
    lista.id = idLista;
    lista.className = "buscador-producto-lista list-group shadow d-none";
    lista.setAttribute("role", "listbox");

    select.parentNode.insertBefore(caja, select);
    caja.appendChild(entrada);
    caja.appendChild(lista);
    caja.appendChild(select);
    // El select queda oculto pero accesible para el formulario y para su <label>.
    select.classList.add("visually-hidden");
    select.tabIndex = -1;
    select.addEventListener("focus", () => entrada.focus());

    let resultados = [];
    let activo = -1;

    const textoElegido = () => (select.value ? select.selectedOptions[0].text : "");
    entrada.value = textoElegido();

    function elegir(opcion) {
      select.value = opcion ? opcion.value : "";
      entrada.value = textoElegido();
      cerrar();
      // Avisa a la página (sugerir precio o costo, recalcular el total).
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function cerrar() {
      lista.classList.add("d-none");
      entrada.setAttribute("aria-expanded", "false");
      entrada.removeAttribute("aria-activedescendant");
      activo = -1;
    }

    function marcar(indice) {
      const items = lista.querySelectorAll("[role=option]");
      items.forEach((item, i) => item.classList.toggle("active", i === indice));
      activo = indice;
      if (items[indice]) {
        entrada.setAttribute("aria-activedescendant", items[indice].id);
        items[indice].scrollIntoView({ block: "nearest" });
      }
    }

    function mostrar() {
      const texto = entrada.value === textoElegido() ? "" : normalizar(entrada.value);
      const palabras = texto.split(/\s+/).filter(Boolean);
      const coinciden = opciones.filter((o) => {
        const donde = o.dataset.buscar || normalizar(o.text);
        return palabras.every((p) => donde.includes(p));
      });
      resultados = coinciden.slice(0, MAX_RESULTADOS);
      lista.innerHTML = "";
      resultados.forEach((opcion, i) => {
        const item = document.createElement("li");
        item.id = `${idLista}-${i}`;
        item.className = "list-group-item list-group-item-action small";
        item.setAttribute("role", "option");
        item.textContent = opcion.text;
        if (opcion.dataset.stock === "0") item.classList.add("text-muted");
        // mousedown (y no click) para elegir antes de que la caja pierda el foco.
        item.addEventListener("mousedown", (e) => { e.preventDefault(); elegir(opcion); });
        lista.appendChild(item);
      });
      if (!resultados.length) {
        lista.innerHTML = '<li class="list-group-item small text-muted">No hay productos con ese texto.</li>';
      } else if (coinciden.length > MAX_RESULTADOS) {
        const mas = document.createElement("li");
        mas.className = "list-group-item small text-muted";
        mas.textContent = `Hay ${coinciden.length - MAX_RESULTADOS} más: escribe más palabras para encontrarlo.`;
        lista.appendChild(mas);
      }
      lista.classList.remove("d-none");
      entrada.setAttribute("aria-expanded", "true");
      marcar(palabras.length && resultados.length ? 0 : -1);
    }

    entrada.addEventListener("focus", () => { entrada.select(); mostrar(); });
    entrada.addEventListener("input", mostrar);
    entrada.addEventListener("keydown", (e) => {
      const abierta = !lista.classList.contains("d-none");
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (!abierta) mostrar();
        marcar(Math.min(activo + 1, resultados.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        marcar(Math.max(activo - 1, 0));
      } else if (e.key === "Enter") {
        if (!abierta) return;
        e.preventDefault(); // Enter elige el producto; no envía el formulario
        const codigo = normalizar(entrada.value);
        const exacto = opciones.find((o) => o.dataset.codigo && o.dataset.codigo === codigo);
        if (exacto) elegir(exacto);
        else if (resultados[activo]) elegir(resultados[activo]);
        else if (resultados.length === 1) elegir(resultados[0]);
      } else if (e.key === "Escape") {
        entrada.value = textoElegido();
        cerrar();
      }
    });
    entrada.addEventListener("blur", () => {
      // Si borró el texto, se quita el producto; si escribió algo sin elegir, vuelve el elegido.
      if (entrada.value.trim() === "" && select.value) elegir(null);
      else entrada.value = textoElegido();
      cerrar();
    });
  }

  document.querySelectorAll("select.buscador-producto").forEach(crearBuscador);
})();
