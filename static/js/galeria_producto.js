/*
 * Galería de fotos del producto (Agregar y Editar producto): compacta y SIN botones.
 *
 * Todas las fotos están en una sola lista; la PRIMERA es la principal.
 *   - Sin fotos: un recuadro bajo; se hace clic para elegirlas o se sueltan ahí (varias a la vez).
 *   - Con fotos: la principal grande (2×2) a la izquierda; a su derecha, las fotos 2 a 6 (las vacías dicen
 *     «+ Foto N») y la casilla «Agregar varias». Mide lo mismo con 1 o con 6 fotos.
 *   - Clic en una foto: se elige otra imagen para REEMPLAZARLA (también la principal).
 *   - Arrastrar una foto sobre otra: se INTERCAMBIAN (así se cambia la principal), sean guardadas o nuevas.
 *   - «✕» (aparece al pasar el mouse; en el celular se ve siempre): la QUITA.
 *   - Celular: mantener presionada una foto medio segundo y arrastrarla a otra casilla. Un toque la reemplaza.
 *   - Teclado: Enter reemplaza, las flechas mueven y Suprimir quita.
 * Nada se guarda hasta presionar «Guardar producto»: al enviar, el orden final va en el campo oculto
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
  var ESPERA_TACTIL = 450;  // ms con el dedo quieto para «levantar» una foto en el celular
  var plan = document.getElementById("id_galeria_plan");
  var entrada = galeria.querySelector("[data-agregar]");
  var reemplazo = galeria.querySelector("[data-reemplazo]");
  var cuerpo = galeria.querySelector("[data-cuerpo]");
  var cajaPrincipal = galeria.querySelector("[data-principal]");
  var cajaSecundarias = galeria.querySelector("[data-secundarias]");
  var avisoCambios = galeria.querySelector("[data-cambios]");
  var avisoError = galeria.querySelector("[data-error]");
  var contador = galeria.querySelector("[data-contador]");
  var ayuda = galeria.querySelector("[data-ayuda]");
  var regla = galeria.querySelector("[data-regla]");

  var iniciales = JSON.parse(document.getElementById("fotos-actuales").textContent || "[]");
  var fotos = iniciales.slice();   // {ficha, url} guardadas o {archivo, url, nueva: true}
  var arrastrada = null;            // índice de la foto que se está arrastrando
  var aReemplazar = null;           // índice de la foto que se va a reemplazar
  var resaltar = null;              // índice que se resalta un momento después de un cambio
  var enfocar = null;               // índice que recibe el foco después de mover con el teclado

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
    resaltar = b;
    avisar("");
    dibujar();
  }

  function quitar(i) {
    fotos.splice(i, 1);
    avisar("");
    dibujar();
  }

  function reemplazar(i) {
    aReemplazar = i;
    reemplazo.value = "";
    reemplazo.click();
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

  function tarjeta(foto, i) {
    var principal = i === 0;
    var nombre = principal ? "Foto principal" : "Foto " + (i + 1);
    var t = elemento("div", "tarjeta-foto " + (principal ? "tarjeta-foto--principal" : "tarjeta-foto--secundaria") + (foto.nueva ? " tarjeta-foto--nueva" : ""));
    t.dataset.indice = i;
    t.tabIndex = 0;
    t.setAttribute("role", "button");
    t.setAttribute("aria-label", nombre + ". Enter: reemplazarla. Flechas: moverla. Suprimir: quitarla.");
    t.title = principal ? "Clic para reemplazar la principal. También puedes soltar aquí otra foto."
      : "Clic para reemplazarla. Arrástrala para cambiarla de lugar.";

    if (principal) {
      var etiqueta = elemento("span", "etiqueta-principal");
      etiqueta.innerHTML = '<span class="numero-foto" title="Se ve primero">1</span><i class="bi bi-star-fill" aria-hidden="true"></i><span class="etiqueta-principal__texto">Principal</span>';
      t.appendChild(etiqueta);
    } else {
      t.appendChild(elemento("span", "numero-foto numero-foto--secundaria", String(i + 1)));
    }

    var x = elemento("button", "tarjeta-foto__x", "×");
    x.type = "button";
    x.title = "Quitar";
    x.setAttribute("aria-label", "Quitar la foto " + (i + 1));
    x.tabIndex = -1;  // con el teclado se quita con Suprimir
    x.addEventListener("click", function (evento) { evento.stopPropagation(); quitar(i); });
    t.appendChild(x);

    var marco = elemento("div", "tarjeta-foto__imagen");
    var img = elemento("img");
    img.src = foto.url;
    img.alt = principal ? "Foto principal" : "Foto " + (i + 1);
    img.draggable = true;
    img.addEventListener("dragstart", function (evento) {
      arrastrada = i;
      evento.dataTransfer.setData(ARRASTRE, String(i));
      evento.dataTransfer.effectAllowed = "move";
      galeria.classList.add("galeria-edicion--arrastrando");
      t.classList.add("tarjeta-foto--arrastrada");
    });
    img.addEventListener("dragend", terminarArrastre);
    marco.appendChild(img);
    t.appendChild(marco);

    // Indicación al pasar el mouse.
    var velo = elemento("div", "tarjeta-foto__velo");
    velo.setAttribute("aria-hidden", "true");
    velo.innerHTML = principal
      ? '<i class="bi bi-arrow-repeat"></i><span>Clic para reemplazar la principal</span><small>o suelta aquí otra foto</small>'
      : '<i class="bi bi-arrow-repeat"></i><span>Reemplazar</span><small>o arrastra para mover</small>';
    t.appendChild(velo);

    t.addEventListener("click", function () {
      if (galeria.dataset.ignorarClic) return;
      reemplazar(i);
    });
    t.addEventListener("keydown", function (evento) {
      var tecla = evento.key;
      if (tecla === "Enter" || tecla === " ") { evento.preventDefault(); reemplazar(i); }
      else if (tecla === "ArrowLeft" || tecla === "ArrowUp") { evento.preventDefault(); if (i > 0) { enfocar = i - 1; intercambiar(i, i - 1); } }
      else if (tecla === "ArrowRight" || tecla === "ArrowDown") { evento.preventDefault(); if (i < fotos.length - 1) { enfocar = i + 1; intercambiar(i, i + 1); } }
      else if (tecla === "Delete" || tecla === "Backspace") { evento.preventDefault(); enfocar = Math.min(i, fotos.length - 2); quitar(i); }
    });
    if (resaltar === i) t.classList.add("tarjeta-foto--intercambiada");
    prepararSoltar(t, i);
    prepararTactil(t, i);
    return t;
  }

  // Sin fotos: un recuadro bajo para elegirlas o soltarlas.
  function zonaVacia() {
    var zona = elemento("label", "galeria-zona");
    zona.htmlFor = entrada.id;
    zona.innerHTML = '<span class="galeria-zona__icono" aria-hidden="true"><i class="bi bi-images"></i></span>' +
      '<span><strong data-zona-titulo>Arrastra tus fotos aquí o <u>elígelas</u></strong>' +
      '<small>JPG, PNG o WEBP · máximo ' + MB + ' MB cada una · hasta ' + MAXIMO + ' fotos</small></span>';
    return zona;
  }

  // Casilla vacía («+ Foto N»): al hacer clic se eligen fotos (varias a la vez).
  function casillaVacia(posicion) {
    var casilla = elemento("label", "casilla-vacia");
    casilla.htmlFor = entrada.id;
    casilla.title = "Agregar fotos (quedan " + (MAXIMO - fotos.length) + "). O arrástralas aquí";
    casilla.innerHTML = '<i class="bi bi-plus-lg" aria-hidden="true"></i><span class="zona-agregar__texto">Foto ' + (posicion + 1) +
      '</span><span class="visually-hidden">: agregar fotos</span>';
    return casilla;
  }

  // Última casilla: «Agregar varias» o, si ya hay 6, «Máximo 6 fotos».
  function casillaFinal(hayLugar) {
    if (!hayLugar) {
      var llena = elemento("div", "casilla-vacia casilla-llena");
      llena.innerHTML = '<i class="bi bi-check2-circle" aria-hidden="true"></i><span>Máximo<br>' + MAXIMO + ' fotos</span>';
      return llena;
    }
    var varias = elemento("label", "casilla-vacia casilla-varias");
    varias.htmlFor = entrada.id;
    varias.title = "Elegir varias fotos a la vez. O arrástralas aquí";
    varias.innerHTML = '<i class="bi bi-upload" aria-hidden="true"></i><span>Agregar varias</span>';
    return varias;
  }

  function dibujar() {
    cajaPrincipal.innerHTML = "";
    cajaSecundarias.innerHTML = "";
    var hayFotos = fotos.length > 0;
    var hayLugar = fotos.length < MAXIMO;
    cuerpo.classList.toggle("galeria-edicion__cuerpo--vacia", !hayFotos);
    if (hayFotos) {
      cajaPrincipal.appendChild(tarjeta(fotos[0], 0));
      for (var i = 1; i < fotos.length; i++) cajaSecundarias.appendChild(tarjeta(fotos[i], i));
      // Las casillas que faltan hasta completar las 6 (la principal + 5) y la casilla final.
      for (var k = fotos.length; k < MAXIMO; k++) cajaSecundarias.appendChild(casillaVacia(k));
      cajaSecundarias.appendChild(casillaFinal(hayLugar));
      ayuda.innerHTML = 'La grande es la principal. <span class="solo-mouse">Haz clic en una foto para reemplazarla o arrástrala para cambiarla de lugar.</span>' +
        '<span class="solo-tactil">Toca una foto para reemplazarla; mantenla presionada para moverla.</span>';
    } else {
      cajaPrincipal.appendChild(zonaVacia());
      ayuda.textContent = "Puedes subir hasta " + MAXIMO + ". La primera será la principal.";
    }
    regla.classList.toggle("d-none", !hayFotos);
    contador.textContent = fotos.length + " de " + MAXIMO;
    avisoCambios.classList.toggle("d-none", !cambiado());
    sincronizar();
    if (enfocar !== null) {
      var destino = galeria.querySelector('.tarjeta-foto[data-indice="' + enfocar + '"]');
      if (destino) destino.focus();
      enfocar = null;
    }
    resaltar = null;
  }

  // ---- Arrastrar y soltar con el mouse ----
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
    galeria.querySelectorAll(".tarjeta-foto--soltar, .tarjeta-foto--arrastrada").forEach(function (c) {
      c.classList.remove("tarjeta-foto--soltar", "tarjeta-foto--arrastrada");
    });
    var titulo = galeria.querySelector("[data-zona-titulo]");
    if (titulo) titulo.innerHTML = "Arrastra tus fotos aquí o <u>elígelas</u>";
  }

  function textoSoltar(i, archivos) {
    if (archivos) return "Suelta para reemplazarla";
    return i === 0 ? "Suelta para que sea la foto principal" : "Suelta para cambiarlas de lugar";
  }

  function prepararSoltar(t, i) {
    t.addEventListener("dragover", function (evento) {
      var foto = traeFoto(evento) && arrastrada !== i;
      if (!foto && !traeArchivos(evento)) return;
      evento.preventDefault();
      evento.stopPropagation();
      t.dataset.soltarTexto = textoSoltar(i, traeArchivos(evento));
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
        if (!isNaN(desde)) intercambiar(desde, i);
        return;
      }
      terminarArrastre();
      if (traeArchivos(evento)) {
        // Una imagen soltada sobre una foto la reemplaza; si eran varias, las demás se agregan.
        var revisadas = validas(evento.dataTransfer.files);
        if (!revisadas.buenas.length) { avisar("No se pudo usar: " + revisadas.problemas.join("; ") + "."); return; }
        fotos[i] = nueva(revisadas.buenas[0]);
        resaltar = i;
        if (revisadas.buenas.length > 1) agregar(revisadas.buenas.slice(1)); else { avisar(""); dibujar(); }
      }
    });
  }

  // Imágenes soltadas en cualquier otro lugar de la galería (recuadro, casillas «+»): se agregan al final.
  galeria.addEventListener("dragover", function (evento) {
    if (!traeArchivos(evento)) return;
    evento.preventDefault();
    galeria.classList.add("galeria-edicion--soltar");
    var titulo = galeria.querySelector("[data-zona-titulo]");
    var cuantas = evento.dataTransfer.items ? evento.dataTransfer.items.length : 0;
    if (titulo) titulo.textContent = cuantas > 1 ? "Suelta para agregar " + cuantas + " fotos" : "Suelta para agregar las fotos";
  });
  galeria.addEventListener("dragleave", function (evento) {
    if (!galeria.contains(evento.relatedTarget)) terminarArrastre();
  });
  galeria.addEventListener("drop", function (evento) {
    if (traeFoto(evento)) { evento.preventDefault(); terminarArrastre(); return; }  // soltó una foto fuera de otra: no pasa nada
    if (!traeArchivos(evento)) return;
    evento.preventDefault();
    terminarArrastre();
    agregar(evento.dataTransfer.files);
  });
  // Si el arrastre termina en cualquier otro lugar de la página, se olvida.
  document.addEventListener("dragend", terminarArrastre);

  // ---- Celular: mantener presionada una foto y arrastrarla ----
  function prepararTactil(t, i) {
    var temporizador = null, levantada = false, inicio = null, fantasma = null, sobre = null;

    function limpiar() {
      clearTimeout(temporizador);
      temporizador = null;
      levantada = false;
      inicio = null;
      if (fantasma) { fantasma.remove(); fantasma = null; }
      if (sobre) { sobre.classList.remove("tarjeta-foto--soltar"); sobre = null; }
      t.classList.remove("tarjeta-foto--levantada");
    }
    function moverFantasma(x, y) {
      fantasma.style.left = x + "px";
      fantasma.style.top = y + "px";
      var debajo = document.elementFromPoint(x, y);
      var destino = debajo && debajo.closest ? debajo.closest(".tarjeta-foto") : null;
      if (destino && (!galeria.contains(destino) || destino === t)) destino = null;
      if (destino === sobre) return;
      if (sobre) sobre.classList.remove("tarjeta-foto--soltar");
      sobre = destino;
      if (sobre) {
        sobre.dataset.soltarTexto = textoSoltar(parseInt(sobre.dataset.indice, 10), false);
        sobre.classList.add("tarjeta-foto--soltar");
      }
    }

    t.addEventListener("touchstart", function (evento) {
      if (evento.touches.length !== 1 || evento.target.closest(".tarjeta-foto__x")) return;
      var dedo = evento.touches[0];
      inicio = { x: dedo.clientX, y: dedo.clientY };
      temporizador = setTimeout(function () {
        levantada = true;
        t.classList.add("tarjeta-foto--levantada");
        fantasma = elemento("div", "foto-fantasma");
        var copia = elemento("img");
        copia.src = fotos[i].url;
        copia.alt = "";
        fantasma.appendChild(copia);
        document.body.appendChild(fantasma);
        moverFantasma(inicio.x, inicio.y);
        if (navigator.vibrate) navigator.vibrate(20);
      }, ESPERA_TACTIL);
    }, { passive: true });

    t.addEventListener("touchmove", function (evento) {
      var dedo = evento.touches[0];
      if (!levantada) {
        // Si el dedo se mueve antes de tiempo, la persona está desplazando la página: no se levanta.
        if (inicio && Math.abs(dedo.clientX - inicio.x) + Math.abs(dedo.clientY - inicio.y) > 10) limpiar();
        return;
      }
      evento.preventDefault();  // mientras se lleva la foto, la página no se desplaza
      moverFantasma(dedo.clientX, dedo.clientY);
    }, { passive: false });

    t.addEventListener("touchend", function (evento) {
      if (!levantada) { limpiar(); return; }
      evento.preventDefault();  // no cuenta como toque (no abre «reemplazar»)
      var hacia = sobre ? parseInt(sobre.dataset.indice, 10) : null;
      limpiar();
      galeria.dataset.ignorarClic = "1";
      setTimeout(function () { delete galeria.dataset.ignorarClic; }, 400);
      if (hacia !== null && !isNaN(hacia)) intercambiar(i, hacia);
    });
    t.addEventListener("touchcancel", limpiar);
    // Que el celular no abra su menú de «guardar imagen» al mantener presionado.
    t.addEventListener("contextmenu", function (evento) { evento.preventDefault(); });
  }

  // ---- Archivos elegidos ----
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
    resaltar = aReemplazar;
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
