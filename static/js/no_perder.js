/*
 * Para no perder lo que se está escribiendo en un formulario largo.
 *
 *   <form data-avisar-salida>        Si se escribió algo y se toca otro enlace, se recarga o se cierra la
 *                                    pestaña, el navegador pregunta antes de salir (el texto del aviso lo
 *                                    pone el navegador, no se puede cambiar).
 *
 *   <form data-borrador="clave"      Borrador automático en ESTE navegador (localStorage, 3 días): si se
 *         data-borrador-titulo="…">  vuelve a la página, ofrece «Recuperar» o «Descartar». Se borra al
 *                                    enviar el formulario.
 *   <form data-borrador-mezclar>     (Conteo) cada página filtrada guarda sus campos sin borrar los de las otras.
 *
 *   <a data-guardar-borrador>        Enlace que sale a otra página y vuelve (p. ej. «+ Crear producto»):
 *                                    guarda el borrador, no pregunta al salir y, al volver, lo recupera solo.
 *
 * Al recuperar, cada campo recibe sus eventos «change»/«input» y el formulario el evento
 * «borrador:restaurado», para que los cálculos de la página se actualicen.
 * No se guardan: la clave de seguridad (csrf), los campos ocultos ni los archivos.
 */
(function () {
  "use strict";
  var PREFIJO = "nexalys_borrador_";
  var VOLVER = "nexalys_borrador_volver";
  var DIAS = 3;
  var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
               "octubre", "noviembre", "diciembre"];

  function leer(clave) {
    try {
      var datos = JSON.parse(localStorage.getItem(PREFIJO + clave) || "null");
      if (!datos || !datos.campos || Date.now() - datos.fecha > DIAS * 864e5) return null;
      return datos;
    } catch (e) { return null; }
  }
  function escribir(clave, datos) {
    try { localStorage.setItem(PREFIJO + clave, JSON.stringify(datos)); } catch (e) { /* sin espacio o navegación privada */ }
  }
  function borrar(clave) {
    try { localStorage.removeItem(PREFIJO + clave); } catch (e) { /* nada */ }
  }
  function sesion(accion, valor) {
    try {
      if (accion === "leer") return sessionStorage.getItem(VOLVER);
      if (accion === "poner") sessionStorage.setItem(VOLVER, valor);
      if (accion === "quitar") sessionStorage.removeItem(VOLVER);
    } catch (e) { return null; }
    return null;
  }

  function campos(form) {
    return Array.prototype.filter.call(form.elements, function (c) {
      return c.name && c.name !== "csrfmiddlewaretoken" && !c.disabled &&
        ["hidden", "file", "submit", "button", "reset", "password"].indexOf(c.type) === -1;
    });
  }
  function valores(form) {
    var datos = {};
    campos(form).forEach(function (c) {
      if (c.type === "checkbox") { (datos[c.name] = datos[c.name] || []); if (c.checked) datos[c.name].push(c.value); }
      else if (c.type === "radio") { if (c.checked) datos[c.name] = c.value; else if (!(c.name in datos)) datos[c.name] = null; }
      else if (c.tagName === "SELECT" && c.multiple) datos[c.name] = Array.prototype.map.call(c.selectedOptions, function (o) { return o.value; });
      else datos[c.name] = c.value;
    });
    return datos;
  }
  function tieneAlgo(datos) {
    return Object.keys(datos).some(function (n) {
      var v = datos[n];
      return Array.isArray(v) ? v.length > 0 : v !== null && v !== "";
    });
  }
  function poner(form, datos) {
    var cambiados = [];
    campos(form).forEach(function (c) {
      if (!(c.name in datos)) return;
      var v = datos[c.name];
      if (c.type === "checkbox") c.checked = Array.isArray(v) && v.indexOf(c.value) !== -1;
      else if (c.type === "radio") c.checked = v === c.value;
      else if (c.tagName === "SELECT" && c.multiple) Array.prototype.forEach.call(c.options, function (o) { o.selected = (v || []).indexOf(o.value) !== -1; });
      else c.value = v == null ? "" : v;
      cambiados.push(c);
    });
    // Primero las listas (eligen el producto), después el resto, para que los cálculos queden bien.
    cambiados.filter(function (c) { return c.tagName === "SELECT"; })
      .forEach(function (c) { c.dispatchEvent(new Event("change", { bubbles: true })); });
    cambiados.filter(function (c) { return c.tagName !== "SELECT"; })
      .forEach(function (c) { c.dispatchEvent(new Event("input", { bubbles: true })); });
    form.dispatchEvent(new CustomEvent("borrador:restaurado", { bubbles: true }));
  }
  function cuando(fecha) {
    var d = new Date(fecha), h = d.getHours() % 12 || 12;
    return "el " + d.getDate() + " de " + MESES[d.getMonth()] + " a las " + h + ":" +
      String(d.getMinutes()).padStart(2, "0") + (d.getHours() < 12 ? " a. m." : " p. m.");
  }

  // ---------- Aviso al salir ----------
  var formulariosConCambios = new Set();
  var salidaPermitida = false;
  document.querySelectorAll("form[data-avisar-salida], form[data-borrador]").forEach(function (form) {
    var marcar = function (evento) { if (evento.isTrusted) formulariosConCambios.add(form); };
    form.addEventListener("input", marcar);
    form.addEventListener("change", marcar);
    form.addEventListener("submit", function () { formulariosConCambios.delete(form); });
  });
  document.addEventListener("click", function (evento) {
    if (evento.target.closest && evento.target.closest("a[data-guardar-borrador]")) salidaPermitida = true;
  });
  window.addEventListener("beforeunload", function (evento) {
    if (salidaPermitida || !formulariosConCambios.size) return;
    evento.preventDefault();
    evento.returnValue = "";  // el navegador muestra su propio «¿Salir del sitio?»
  });

  // ---------- Borrador automático ----------
  document.querySelectorAll("form[data-borrador]").forEach(function (form) {
    var clave = form.dataset.borrador;
    var mezclar = form.hasAttribute("data-borrador-mezclar");
    var titulo = form.dataset.borradorTitulo || "formulario";
    var guardado = leer(clave);
    var listo = false;  // no se guarda nada hasta decidir qué hacer con el borrador anterior
    var temporizador = null;

    function guardar() {
      if (!listo) return;
      var actuales = valores(form);
      var previos = mezclar && leer(clave) ? leer(clave).campos : {};
      var todos = Object.assign({}, previos, actuales);
      if (tieneAlgo(todos)) escribir(clave, { fecha: Date.now(), campos: todos });
      else borrar(clave);
    }
    function programar() { clearTimeout(temporizador); temporizador = setTimeout(guardar, 400); }

    form.addEventListener("input", programar);
    form.addEventListener("change", programar);
    form.addEventListener("submit", function () {
      clearTimeout(temporizador);
      if (!mezclar) { borrar(clave); return; }
      var datos = leer(clave);
      if (!datos) return;
      campos(form).forEach(function (c) { delete datos.campos[c.name]; });
      if (tieneAlgo(datos.campos)) escribir(clave, datos); else borrar(clave);
    });
    // «+ Crear producto»: se guarda ya y, al volver, se recupera sin preguntar.
    document.querySelectorAll("a[data-guardar-borrador]").forEach(function (enlace) {
      enlace.addEventListener("click", function () {
        listo = true;
        guardar();
        sesion("poner", clave);
      });
    });

    function recuperar() {
      listo = true;
      poner(form, guardado.campos);
      formulariosConCambios.add(form);
      guardar();
    }

    // ¿Hay algo que recuperar en ESTA página? (en el conteo, solo los campos que se ven aquí)
    var nombresAqui = campos(form).map(function (c) { return c.name; });
    var util = guardado && Object.keys(guardado.campos).some(function (n) {
      var v = guardado.campos[n];
      return nombresAqui.indexOf(n) !== -1 && (Array.isArray(v) ? v.length : v !== null && v !== "");
    });
    var volviendo = sesion("leer") === clave;
    sesion("quitar");

    if (!util) { listo = true; return; }
    if (volviendo) { recuperar(); return; }

    var aviso = document.createElement("div");
    aviso.className = "aviso-borrador";
    aviso.setAttribute("role", "status");
    aviso.innerHTML = '<i class="bi bi-clock-history" aria-hidden="true"></i><span></span>' +
      '<button type="button" class="btn btn-sm btn-primary" data-recuperar>Recuperar</button>' +
      '<button type="button" class="btn btn-sm btn-outline-secondary" data-descartar>Descartar</button>';
    aviso.querySelector("span").textContent = "Tienes un " + titulo + " sin terminar (" + cuando(guardado.fecha) + ").";
    aviso.querySelector("[data-recuperar]").addEventListener("click", function () {
      recuperar();
      aviso.remove();
    });
    aviso.querySelector("[data-descartar]").addEventListener("click", function () {
      if (mezclar) {
        nombresAqui.forEach(function (n) { delete guardado.campos[n]; });
        if (tieneAlgo(guardado.campos)) escribir(clave, guardado); else borrar(clave);
      } else {
        borrar(clave);
      }
      listo = true;
      aviso.remove();
    });
    form.parentNode.insertBefore(aviso, form);
  });

  // Para pruebas.
  window.NexalysBorrador = { valores: valores, poner: poner };
})();
