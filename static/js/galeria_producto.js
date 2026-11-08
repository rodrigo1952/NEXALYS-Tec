/*
 * Galería de fotos del producto (Agregar y Editar producto).
 *
 * Todas las fotos están en una sola lista; la PRIMERA es la principal.
 *   - «+ Agregar fotos» (o soltar imágenes en la galería): se suman al final, hasta el máximo.
 *   - Arrastrar una foto sobre otra las intercambia, sean fotos guardadas o nuevas.
 *   - «Hacer principal» (★), «Reemplazar» (⟳), las flechas ‹ › y la «X» hacen lo mismo con botones
 *     (en el celular no se puede arrastrar).
 * La principal va arriba con tamaño fijo y debajo siempre hay 5 casillas iguales (las vacías con «+»),
 * así la galería mide lo mismo con 1 o con 6 fotos.
 * Nada se guarda hasta presionar «Guardar»: al enviar, el orden final va en el campo oculto
 * «galeria_plan» (p = principal actual, f12 = foto adicional 12, n0 = primera foto nueva) y
 * las fotos nuevas, en ese mismo orden, en «fotos_nuevas». El servidor revisa todo otra vez.
 */
(function () {
  "use strict";
  var galeria = document.querySelector("[data-galeria]");
  if (!galeria || !window.DataTransfer) return;
  var MAXIMO = parseInt(galeria.dataset.maximo, 10) || 6;
  var MB = 2;
  var TIPOS = ["image/jpeg", "image/png", "image/webp"];
  var ARRASTRE = "application/x-nexalys-foto";
  var plan = document.getElementById("id_galeria_plan");
  var entrada = galeria.querySelector("[data-agregar]");
  var reemplazo = galeria.querySelector("[data-reemplazo]");
  var cajaPrincipal = galeria.querySelector("[data-principal]");
  var cajaSecundarias = galeria.querySelector("[data-secundarias]");
  var avisoCambios = galeria.querySelector("[data-cambios]");
  var avisoError = galeria.querySelector("[data-error]");
  var contador = galeria.querySelector("[data-contador]");
  var botonAgregar = galeria.querySelector("[data-boton-agregar]");

  var iniciales = JSON.parse(document.getElementById("fotos-actuales").textContent || "[]");
  var fotos = iniciales.slice();   // {ficha, url} guardadas o {archivo, url, nueva: true}
  var arrastrada = null;            // índice de la foto que se está arrastrando
  var aReemplazar = null;           // índice de la foto que se va a reemplazar

  function avisar(texto) {
    avisoError.textContent = texto || "";
    avisoError.classList.toggle("d-none", !texto);
  }

  // Solo imágenes JPG, PNG o WEBP de hasta 2 MB (el servidor también lo revisa).
  function validas(archivos) {
    var buenas = [], problemas = [];
    Array.prototype.forEach.call(archivos, function (archivo) {
      if (TIPOS.indexOf(archivo.type) === -1) problemas.push(archivo.name + " no es JPG, PNG ni WEBP");
      else if (archivo.size > MB * 1024 * 1024) problemas.push(archivo.name + " pesa más de " + MB + " MB");
      else buenas.push(archivo);
    });
    return { buenas: buenas, problemas: problemas };
  }

  function nueva(archivo) {
    return { archivo: archivo, url: URL.createObjectURL(archivo), nueva: true };
  }

  function agregar(archivos) {
    var revisadas = validas(archivos);
    var libres = MAXIMO - fotos.length;
    var mensajes = revisadas.problemas.slice();
    if (revisadas.buenas.length > libres) {
      mensajes.push("solo caben " + Math.max(libres, 0) + " foto(s) más (máximo " + MAXIMO + "): las demás no se agregaron");
    }
    revisadas.buenas.slice(0, Math.max(libres, 0)).forEach(function (archivo) { fotos.push(nueva(archivo)); });
    avisar(mensajes.length ? "No se agregaron todas: " + mensajes.join("; ") + "." : "");
    dibujar();
  }

  function intercambiar(a, b) {
    if (a === b || a < 0 || b < 0 || a >= fotos.length || b >= fotos.length) return;
    var copia = fotos[a];
    fotos[a] = fotos[b];
    fotos[b] = copia;
    avisar("");
    dibujar();
  }

  function cambiado() {
    return fotos.length !== iniciales.length || fotos.some(function (foto, i) { return foto !== iniciales[i]; });
  }

  // Deja listos los campos que se envían al guardar.
  function sincronizar() {
    var transferencia = new DataTransfer();
    var n = 0;
    var fichas = fotos.map(function (foto) {
      if (!foto.nueva) return foto.ficha;
      transferencia.items.add(foto.archivo);
      return "n" + (n++);
    });
    entrada.files = transferencia.files;
    plan.value = fichas.length ? fichas.join(",") : "ninguna";
  }

  // ---- Dibujo ----
  function elemento(etiqueta, clase, texto) {
    var el = document.createElement(etiqueta);
    if (clase) el.className = clase;
    if (texto) el.textContent = texto;
    return el;
  }

  function boton(texto, clase, alPresionar, etiquetaAccesible) {
    var b = elemento("button", "btn btn-sm " + clase, texto);
    b.type = "button";
    if (etiquetaAccesible) b.setAttribute("aria-label", etiquetaAccesible);
    b.addEventListener("click", alPresionar);
    return b;
  }

  // Botón pequeño con solo un ícono; al pasar el mouse muestra qué hace (title).
  function botonIcono(icono, titulo, alPresionar, numero, deshabilitado) {
    var b = boton("", "btn-outline-secondary boton-icono", alPresionar, titulo + " (foto " + numero + ")");
    b.innerHTML = '<i class="bi ' + icono + '" aria-hidden="true"></i>';
    b.title = titulo;
    b.disabled = !!deshabilitado;
    return b;
  }

  function tarjeta(foto, i) {
    var principal = i === 0;
    var t = elemento("div", "tarjeta-foto " + (principal ? "tarjeta-foto--principal" : "tarjeta-foto--secundaria") + (foto.nueva ? " tarjeta-foto--nueva" : ""));
    t.dataset.indice = i;
    if (principal) {
      var etiqueta = elemento("span", "etiqueta-principal");
      etiqueta.innerHTML = '<span class="numero-foto" title="Se ve primero">1</span><span aria-hidden="true">★</span> Foto principal';
      t.appendChild(etiqueta);
    } else {
      t.appendChild(elemento("span", "numero-foto numero-foto--secundaria", String(i + 1)));
    }
    if (foto.nueva) t.appendChild(elemento("span", "etiqueta-nueva" + (principal ? " etiqueta-nueva--principal" : ""), "Nueva"));
    var x = boton("×", "tarjeta-foto__x", function () { fotos.splice(i, 1); avisar(""); dibujar(); }, "Quitar la foto " + (i + 1));
    x.classList.remove("btn", "btn-sm");
    x.title = "Quitar";
    t.appendChild(x);

    var marco = elemento("div", "tarjeta-foto__imagen");
    var img = elemento("img");
    img.src = foto.url;
    img.alt = principal ? "Foto principal" : "Foto " + (i + 1);
    img.draggable = true;
    img.title = "Arrástrala sobre otra foto para cambiarlas de lugar";
    img.addEventListener("dragstart", function (evento) {
      arrastrada = i;
      evento.dataTransfer.setData(ARRASTRE, String(i));
      evento.dataTransfer.effectAllowed = "move";
      galeria.classList.add("galeria-edicion--arrastrando");
    });
    img.addEventListener("dragend", terminarArrastre);
    marco.appendChild(img);
    t.appendChild(marco);

    function reemplazar() {
      aReemplazar = i;
      reemplazo.value = "";
      reemplazo.click();
    }
    if (principal) {
      var pie = elemento("div", "tarjeta-foto__pie");
      pie.appendChild(elemento("p", "small text-muted mb-0", "Es la que se ve en el catálogo y en el inicio."));
      pie.appendChild(boton("Cambiar foto principal", "btn-outline-primary", reemplazar));
      t.appendChild(pie);
    } else {
      // Siempre los 4 botones en el mismo lugar; las flechas se apagan en los extremos.
      var botones = elemento("div", "tarjeta-foto__botones");
      botones.appendChild(botonIcono("bi-star-fill", "Hacer principal", function () { intercambiar(0, i); }, i + 1));
      botones.appendChild(botonIcono("bi-arrow-repeat", "Reemplazar", reemplazar, i + 1));
      botones.appendChild(botonIcono("bi-chevron-left", "Mover a la izquierda", function () { intercambiar(i, i - 1); }, i + 1, i <= 1));
      botones.appendChild(botonIcono("bi-chevron-right", "Mover a la derecha", function () { intercambiar(i, i + 1); }, i + 1, i >= fotos.length - 1));
      t.appendChild(botones);
    }
    prepararSoltar(t, i);
    return t;
  }

  function principalVacia() {
    var t = elemento("label", "tarjeta-foto tarjeta-foto--principal tarjeta-foto--vacia");
    t.htmlFor = entrada.id;
    var etiqueta = elemento("span", "etiqueta-principal");
    etiqueta.innerHTML = '<span class="numero-foto">1</span><span aria-hidden="true">★</span> Foto principal';
    t.appendChild(etiqueta);
    var marco = elemento("div", "tarjeta-foto__imagen flex-column gap-2 text-center px-3");
    marco.innerHTML = '<i class="bi bi-images fs-1 text-muted" aria-hidden="true"></i>' +
      '<span class="fw-semibold">Elige hasta ' + MAXIMO + ' fotos</span>' +
      '<span class="small text-muted">La primera será la principal. También puedes arrastrarlas aquí.</span>';
    t.appendChild(marco);
    t.appendChild(elemento("span", "btn btn-sm btn-primary align-self-start", "Subir fotos"));
    prepararSoltar(t, 0);
    return t;
  }

  // Casilla vacía (mismo tamaño que una foto adicional): al hacer clic se eligen más fotos.
  function casillaVacia(primera) {
    var quedan = MAXIMO - fotos.length;
    var casilla = elemento("label", "tarjeta-foto tarjeta-foto--secundaria casilla-vacia mb-0");
    casilla.htmlFor = entrada.id;
    casilla.title = "Agregar fotos (quedan " + quedan + "). O arrástralas aquí";
    var zona = elemento("span", "tarjeta-foto__imagen zona-agregar");
    zona.innerHTML = '<span class="zona-agregar__mas" aria-hidden="true">+</span>' +
      (primera ? '<span class="zona-agregar__texto">Agregar fotos</span>' : '<span class="visually-hidden">Agregar fotos</span>');
    casilla.appendChild(zona);
    var espacio = elemento("span", "tarjeta-foto__botones");  // mismo alto que los botones de las fotos
    espacio.setAttribute("aria-hidden", "true");
    casilla.appendChild(espacio);
    return casilla;
  }

  function dibujar() {
    cajaPrincipal.innerHTML = "";
    cajaSecundarias.innerHTML = "";
    cajaPrincipal.appendChild(fotos.length ? tarjeta(fotos[0], 0) : principalVacia());
    for (var i = 1; i < fotos.length; i++) cajaSecundarias.appendChild(tarjeta(fotos[i], i));
    var hayLugar = fotos.length < MAXIMO;
    // Las casillas que faltan hasta completar las 5 adicionales.
    for (var k = Math.max(fotos.length, 1); k < MAXIMO; k++) cajaSecundarias.appendChild(casillaVacia(k === Math.max(fotos.length, 1)));
    botonAgregar.classList.toggle("invisible", !hayLugar);  // invisible (no d-none): así la galería no cambia de alto
    contador.textContent = "Tienes " + fotos.length + " de " + MAXIMO + " fotos.";
    avisoCambios.classList.toggle("d-none", !cambiado());
    sincronizar();
  }

  // ---- Arrastrar y soltar ----
  // OJO: al arrastrar una foto de la página, Chrome/Brave/Edge también la ponen como «archivo»
  // (Files). Por eso PRIMERO se pregunta si es una foto de la galería; solo si no lo es, se trata
  // como imágenes que vienen de tu carpeta. Si no, la foto arrastrada se copiaba encima de la otra.
  function traeFoto(evento) {
    return arrastrada !== null || Array.prototype.indexOf.call(evento.dataTransfer.types, ARRASTRE) !== -1;
  }
  function traeArchivos(evento) {
    return !traeFoto(evento) && Array.prototype.indexOf.call(evento.dataTransfer.types, "Files") !== -1;
  }
  function terminarArrastre() {
    arrastrada = null;
    galeria.classList.remove("galeria-edicion--arrastrando", "galeria-edicion--soltar");
    galeria.querySelectorAll(".tarjeta-foto--soltar").forEach(function (c) { c.classList.remove("tarjeta-foto--soltar"); });
  }

  function prepararSoltar(t, i) {
    var vacia = !fotos.length;
    t.addEventListener("dragover", function (evento) {
      var foto = traeFoto(evento) && arrastrada !== i && !vacia;
      if (!foto && !traeArchivos(evento)) return;
      evento.preventDefault();
      evento.stopPropagation();
      t.dataset.soltarTexto = vacia ? "Suelta para agregarlas"
        : traeArchivos(evento) ? "Suelta para reemplazarla"
        : i === 0 ? "Suelta para que sea la foto principal" : "Suelta para cambiarlas de lugar";
      t.classList.add("tarjeta-foto--soltar");
    });
    t.addEventListener("dragleave", function (evento) {
      if (!t.contains(evento.relatedTarget)) t.classList.remove("tarjeta-foto--soltar");
    });
    t.addEventListener("drop", function (evento) {
      evento.preventDefault();
      evento.stopPropagation();
      if (traeFoto(evento)) {
        // Foto de la galería soltada sobre otra: se intercambian.
        var desde = arrastrada !== null ? arrastrada : parseInt(evento.dataTransfer.getData(ARRASTRE), 10);
        terminarArrastre();
        if (!isNaN(desde) && !vacia) intercambiar(desde, i);
        return;
      }
      terminarArrastre();
      if (traeArchivos(evento)) {
        if (vacia) { agregar(evento.dataTransfer.files); return; }
        // Una imagen soltada sobre una foto la reemplaza; si eran varias, las demás se agregan.
        var revisadas = validas(evento.dataTransfer.files);
        if (!revisadas.buenas.length) { avisar("No se pudo usar: " + revisadas.problemas.join("; ") + "."); return; }
        fotos[i] = nueva(revisadas.buenas[0]);
        if (revisadas.buenas.length > 1) agregar(revisadas.buenas.slice(1)); else { avisar(""); dibujar(); }
      }
    });
  }

  // Imágenes soltadas en cualquier otro lugar de la galería: se agregan al final.
  galeria.addEventListener("dragover", function (evento) {
    if (!traeArchivos(evento)) return;
    evento.preventDefault();
    galeria.classList.add("galeria-edicion--soltar");
  });
  galeria.addEventListener("dragleave", function (evento) {
    if (!galeria.contains(evento.relatedTarget)) galeria.classList.remove("galeria-edicion--soltar");
  });
  galeria.addEventListener("drop", function (evento) {
    if (traeFoto(evento)) { evento.preventDefault(); terminarArrastre(); return; }  // soltó una foto fuera de otra: no pasa nada
    if (!traeArchivos(evento)) return;
    evento.preventDefault();
    galeria.classList.remove("galeria-edicion--soltar");
    agregar(evento.dataTransfer.files);
  });
  // Si el arrastre termina en cualquier otro lugar de la página, se olvida.
  document.addEventListener("dragend", terminarArrastre);

  // ---- Botones y archivos ----
  entrada.addEventListener("change", function () {
    // El navegador deja aquí SOLO lo que se acaba de elegir: se suma a la lista y se vuelve a armar.
    var elegidas = Array.prototype.slice.call(entrada.files);
    if (elegidas.length) agregar(elegidas); else sincronizar();
  });
  reemplazo.addEventListener("change", function () {
    if (aReemplazar === null || !reemplazo.files.length) return;
    var revisadas = validas(reemplazo.files);
    if (!revisadas.buenas.length) { avisar("No se pudo usar: " + revisadas.problemas.join("; ") + "."); return; }
    fotos[aReemplazar] = nueva(revisadas.buenas[0]);
    aReemplazar = null;
    avisar("");
    dibujar();
  });
  galeria.querySelector("[data-deshacer]").addEventListener("click", function () {
    fotos = iniciales.slice();
    avisar("");
    dibujar();
  });
  // Justo antes de enviar se vuelven a armar los campos (por si el navegador vació la selección).
  galeria.closest("form").addEventListener("submit", sincronizar);

  dibujar();
})();
